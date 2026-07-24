"""
Import city client Excel files into BookingReportClient.

Supports:
  - Old format: Client Name | Mobile
  - New format: Sr No. | Client Name | Mobile | City

Usage:
  python manage.py import_booking_client_report --replace \\
    partner/Clients_Mumbai_All_2026-07-24.xlsx \\
    partner/Clients_Pune_2026-07-24.xlsx

  python manage.py import_booking_client_report --city Mumbai path/to/file.xlsx
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from core.models import BookingReportClient


def _norm_header(value) -> str:
    return str(value or '').strip().lower().replace('.', '').replace('_', ' ')


def _detect_columns(header) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, col in enumerate(header or []):
        h = _norm_header(col)
        if h in {'client name', 'name', 'customer name'}:
            mapping['name'] = idx
        elif h in {'mobile', 'phone', 'number', 'mobile number'}:
            mapping['mobile'] = idx
        elif h in {'city'}:
            mapping['city'] = idx
    return mapping


class Command(BaseCommand):
    help = 'Import Mumbai/Pune client Excel (name + mobile + city) into BookingReportClient'

    def add_arguments(self, parser):
        parser.add_argument(
            'xlsx_paths',
            nargs='+',
            type=str,
            help='One or more .xlsx paths (Mumbai and/or Pune files)',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Delete all existing BookingReportClient rows before import',
        )
        parser.add_argument(
            '--city',
            type=str,
            default='',
            help='Fallback city when Excel has no City column (e.g. Mumbai / Pune)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=2000,
            help='Bulk create batch size (default 2000)',
        )

    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError as exc:
            raise CommandError('openpyxl is required. Run: pip install openpyxl') from exc

        paths = []
        for raw in options['xlsx_paths']:
            path = Path(raw).expanduser().resolve()
            if not path.exists():
                raise CommandError(f'File not found: {path}')
            if path.suffix.lower() not in {'.xlsx', '.xlsm'}:
                raise CommandError(f'Only .xlsx files are supported: {path}')
            paths.append(path)

        batch_size = max(100, int(options['batch_size']))
        fallback_city = (options.get('city') or '').strip()
        created = 0
        skipped = 0
        batch: list[BookingReportClient] = []

        with transaction.atomic():
            if options['replace']:
                deleted, _ = BookingReportClient.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'Deleted existing rows: {deleted}'))

            for path in paths:
                self.stdout.write(f'Importing {path.name}…')
                wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                ws = wb.active
                rows_iter = ws.iter_rows(values_only=True)
                header = next(rows_iter, None)
                cols = _detect_columns(header)

                # Fallback for old 2-col or new 4-col without perfect headers
                if 'name' not in cols or 'mobile' not in cols:
                    if header and len(header) >= 4:
                        cols = {'name': 1, 'mobile': 2, 'city': 3}
                    elif header and len(header) >= 2:
                        cols = {'name': 0, 'mobile': 1}
                    else:
                        wb.close()
                        raise CommandError(
                            f'{path.name}: expected Client Name + Mobile columns (got {header!r})'
                        )

                # Dataset city from filename / --city (Mumbai Excel → Mumbai, Pune Excel → Pune).
                # This keeps API ?city=Mumbai / ?city=Pune filters clean even when Excel
                # City column has localities (Thane, Navi Mumbai, etc.).
                file_city_hint = ''
                lower_name = path.name.lower()
                if 'mumbai' in lower_name:
                    file_city_hint = 'Mumbai'
                elif 'pune' in lower_name:
                    file_city_hint = 'Pune'
                dataset_city = fallback_city or file_city_hint

                for row in rows_iter:
                    name_raw = row[cols['name']] if len(row) > cols['name'] else None
                    mobile_raw = row[cols['mobile']] if len(row) > cols['mobile'] else None
                    city_raw = None
                    if 'city' in cols and len(row) > cols['city']:
                        city_raw = row[cols['city']]

                    name = str(name_raw).strip() if name_raw is not None else ''
                    mobile = str(mobile_raw).strip() if mobile_raw is not None else ''
                    mobile = ''.join(ch for ch in mobile if ch.isdigit())

                    if dataset_city:
                        city = dataset_city
                    else:
                        city = str(city_raw).strip() if city_raw is not None else ''
                        city_l = city.lower()
                        if 'mumbai' in city_l:
                            city = 'Mumbai'
                        elif 'pune' in city_l:
                            city = 'Pune'

                    if not name and not mobile:
                        skipped += 1
                        continue
                    if not name:
                        name = 'Unknown'
                    if not mobile:
                        skipped += 1
                        continue

                    batch.append(
                        BookingReportClient(
                            name=name[:255],
                            mobile=mobile[:20],
                            city=(city or '')[:50],
                        )
                    )
                    if len(batch) >= batch_size:
                        BookingReportClient.objects.bulk_create(batch, batch_size=batch_size)
                        created += len(batch)
                        batch.clear()
                        self.stdout.write(f'Imported {created}…')

                wb.close()

            if batch:
                BookingReportClient.objects.bulk_create(batch, batch_size=batch_size)
                created += len(batch)

        total = BookingReportClient.objects.count()
        by_city = {
            row['city'] or '(blank)': row['c']
            for row in BookingReportClient.objects.values('city').annotate(c=Count('id'))
        }
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. created={created} skipped={skipped} table_total={total} by_city={by_city}'
            )
        )
