"""Load the 2026 master rate chart into Pricing Master.

The workbook quotes a GST-exclusive "Recommended Basic" plus 18% GST, so rows
land with price_includes_gst=False and amount = basic. The CRM then derives GST
and the final payable, which reproduces the workbook's own total column.

    # see what would change, touch nothing
    python manage.py import_rate_chart_2026 --dry-run

    # load into both priced regions
    python manage.py import_rate_chart_2026

    # Mumbai only, leaving existing rows alone
    python manage.py import_rate_chart_2026 --region mumbai --skip-existing

Re-running is safe: rows are matched on the natural key
(region, service_package, plan_type, area_key) and updated in place.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import (
    PricingRate,
    PricingRateAuditAction,
    PricingRateAuditLog,
    PricingRegion,
)
from core.pricing.gst import gst_breakdown

DATA_FILE = Path(__file__).resolve().parents[3] / 'core' / 'pricing' / 'data' / 'rate_chart_2026.csv'

# The workbook's own header lists the cities this one card covers, so it applies
# to every priced region rather than to Mumbai alone.
DEFAULT_REGIONS = ('mumbai', 'lonavala')

SOURCE_NOTE = 'Master Rate Chart 2026 (v2026-09-07)'


def payable(amount: Decimal, *, includes_gst: bool, gst_percent: Decimal) -> Decimal:
    return Decimal(str(gst_breakdown(
        amount, gst_percent=gst_percent, price_includes_gst=includes_gst,
    )['total_with_gst']))


class Command(BaseCommand):
    help = 'Import the 2026 master rate chart (GST-exclusive basics) into Pricing Master.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            action='append',
            metavar='SLUG',
            help=(
                'Pricing region slug to load into; repeatable. '
                f'Defaults to {", ".join(DEFAULT_REGIONS)}.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report the changes without writing them.',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Only insert missing rates; never change a rate that already exists.',
        )
        parser.add_argument(
            '--deactivate-legacy',
            action='store_true',
            help=(
                'Deactivate rates in the target regions that the chart does not '
                'mention, so the booking form stops offering the old vocabulary.'
            ),
        )
        parser.add_argument(
            '--purge-chart',
            action='store_true',
            help=(
                'Delete rates from a previous run of this command before importing. '
                'Needed when a service or area was renamed, since the row is matched '
                'on those values and would otherwise be left behind under its old '
                'name. Rates never imported from the chart are untouched.'
            ),
        )
        parser.add_argument(
            '--file',
            default=str(DATA_FILE),
            help='Override the CSV path.',
        )

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            raise CommandError(
                f'{path} not found. Regenerate it with '
                'scripts/extract_rate_chart_2026.py.'
            )

        with path.open(newline='') as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            raise CommandError(f'{path} has no rows.')

        slugs = options['region'] or list(DEFAULT_REGIONS)
        regions = []
        for slug in slugs:
            try:
                regions.append(PricingRegion.objects.get(slug=slug))
            except PricingRegion.DoesNotExist as exc:
                known = ', '.join(PricingRegion.objects.values_list('slug', flat=True))
                raise CommandError(
                    f'No pricing region {slug!r}. Known regions: {known or "none"}.'
                ) from exc

        dry_run = options['dry_run']
        with transaction.atomic():
            for region in regions:
                self._load_region(region, rows, options)
            if dry_run:
                self.stdout.write(self.style.WARNING('\nDry run - rolling back.'))
                transaction.set_rollback(True)

    def _load_region(self, region, rows, options):
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']

        purged = 0
        if options['purge_chart']:
            prior = PricingRate.objects.filter(
                region=region, notes__startswith=SOURCE_NOTE,
            )
            purged = prior.count()
            if not dry_run:
                prior.delete()

        existing = {
            (r.service_package, r.plan_type, r.area_key): r
            for r in PricingRate.objects.filter(region=region)
        }

        created = updated = unchanged = skipped = 0
        repriced = []

        for row in rows:
            key = (row['service_package'], row['plan_type'], row['area_key'])
            amount = Decimal(row['amount'])
            gst_percent = Decimal(row['gst_percent'])
            floor = Decimal(row['floor_amount']) if row['floor_amount'] else None
            fields = {
                'property_category': row['property_category'],
                'amount': amount,
                'floor_amount': floor,
                'billing_basis': row['billing_basis'],
                'gst_percent': gst_percent,
                # The chart states basics; GST is added on top.
                'price_includes_gst': False,
                'is_active': True,
                'notes': f'{SOURCE_NOTE}. {row["notes"]}'.strip().rstrip('.') + '.',
            }

            rate = existing.get(key)
            if rate is None:
                created += 1
                if not dry_run:
                    rate = PricingRate.objects.create(
                        region=region,
                        service_package=key[0],
                        plan_type=key[1],
                        area_key=key[2],
                        **fields,
                    )
                    self._audit(rate, PricingRateAuditAction.CREATE, None, amount)
                continue

            if skip_existing:
                skipped += 1
                continue

            old_payable = payable(
                rate.amount,
                includes_gst=rate.price_includes_gst,
                gst_percent=rate.gst_percent,
            )
            new_payable = payable(amount, includes_gst=False, gst_percent=gst_percent)
            dirty = any(getattr(rate, f) != v for f, v in fields.items())
            if not dirty:
                unchanged += 1
                continue

            old_amount = rate.amount
            updated += 1
            if old_payable != new_payable:
                repriced.append((key, old_payable, new_payable))
            if not dry_run:
                for field, value in fields.items():
                    setattr(rate, field, value)
                rate.save(update_fields=[*fields, 'updated_at'])
                self._audit(rate, PricingRateAuditAction.UPDATE, old_amount, amount)

        deactivated = 0
        if options['deactivate_legacy']:
            chart_keys = {
                (r['service_package'], r['plan_type'], r['area_key']) for r in rows
            }
            for key, rate in existing.items():
                if key in chart_keys or not rate.is_active:
                    continue
                deactivated += 1
                if not dry_run:
                    rate.is_active = False
                    rate.save(update_fields=['is_active', 'updated_at'])
                    self._audit(
                        rate, PricingRateAuditAction.DEACTIVATE, rate.amount, rate.amount,
                        note='Not present in Master Rate Chart 2026.',
                    )

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{region.name} ({region.slug})'))
        if purged:
            self.stdout.write(f'  purged {purged} rate(s) from an earlier import')
        self.stdout.write(
            f'  created {created}  updated {updated}  unchanged {unchanged}'
            f'  skipped {skipped}  deactivated {deactivated}'
        )
        if repriced:
            self.stdout.write(
                self.style.WARNING(f'  {len(repriced)} rate(s) change what a customer pays:')
            )
            for (service, plan, area), was, now in repriced:
                arrow = 'up' if now > was else 'down'
                self.stdout.write(
                    f'    {service} | {plan} | {area}: {was} -> {now} ({arrow})'
                )

    def _audit(self, rate, action, old_amount, new_amount, note=SOURCE_NOTE):
        PricingRateAuditLog.objects.create(
            rate=rate,
            region_slug=rate.region.slug,
            service_package=rate.service_package,
            plan_type=rate.plan_type,
            area_key=rate.area_key,
            property_category=rate.property_category,
            old_amount=old_amount,
            new_amount=new_amount,
            action=action,
            change_note=note,
        )
