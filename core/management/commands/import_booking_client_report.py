"""
Import BookingClientReport Excel into BookingReportClient.

Usage:
  python manage.py import_booking_client_report "/path/to/BookingClientReport_2026-07-11.xlsx"
  python manage.py import_booking_client_report --replace "/path/to/file.xlsx"
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import BookingReportClient


class Command(BaseCommand):
    help = 'Import BookingClientReport.xlsx (Client Name + Mobile) into BookingReportClient'

    def add_arguments(self, parser):
        parser.add_argument('xlsx_path', type=str, help='Path to BookingClientReport .xlsx file')
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Delete all existing BookingReportClient rows before import',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=2000,
            help='Bulk create batch size (default 2000)',
        )

    def handle(self, *args, **options):
        path = Path(options['xlsx_path']).expanduser().resolve()
        if not path.exists():
            raise CommandError(f'File not found: {path}')
        if path.suffix.lower() not in {'.xlsx', '.xlsm'}:
            raise CommandError('Only .xlsx files are supported')

        try:
            import openpyxl
        except ImportError as exc:
            raise CommandError('openpyxl is required. Run: pip install openpyxl') from exc

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active

        rows_iter = ws.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if not header or len(header) < 2:
            wb.close()
            raise CommandError('Expected header row with at least Client Name and Mobile columns')

        batch_size = max(100, int(options['batch_size']))
        created = 0
        skipped = 0
        batch: list[BookingReportClient] = []

        with transaction.atomic():
            if options['replace']:
                deleted, _ = BookingReportClient.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'Deleted existing rows: {deleted}'))

            for row in rows_iter:
                name_raw = row[0] if len(row) > 0 else None
                mobile_raw = row[1] if len(row) > 1 else None
                name = str(name_raw).strip() if name_raw is not None else ''
                mobile = str(mobile_raw).strip() if mobile_raw is not None else ''
                mobile = ''.join(ch for ch in mobile if ch.isdigit())

                if not name and not mobile:
                    skipped += 1
                    continue
                if not name:
                    name = 'Unknown'
                if not mobile:
                    skipped += 1
                    continue

                batch.append(BookingReportClient(name=name[:255], mobile=mobile[:20]))
                if len(batch) >= batch_size:
                    BookingReportClient.objects.bulk_create(batch, batch_size=batch_size)
                    created += len(batch)
                    batch.clear()
                    self.stdout.write(f'Imported {created}…')

            if batch:
                BookingReportClient.objects.bulk_create(batch, batch_size=batch_size)
                created += len(batch)

        wb.close()
        total = BookingReportClient.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. created={created} skipped={skipped} table_total={total}'
            )
        )
