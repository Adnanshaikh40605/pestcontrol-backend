"""
Cleanup / heal production data for Technician Ledger issues.

- Cancel auto-generated Termite checkup / AMC-followup children (Termite = One-Time only)
- Rewrite Termite-only mains still flagged as AMC
- Backfill missing multi-service day-1 children + recalculate per-service 40%
- Force-recalculate Bed Bugs (÷2) and 2-tech equal split
- Sync AMC → One-Time edits onto ledger flags / cancel stale AMC children
- Heal reported production booking IDs

Usage:
  python manage.py cleanup_technician_ledger_data --dry-run
  python manage.py cleanup_technician_ledger_data
  python manage.py cleanup_technician_ledger_data --ids 2171,2252,2088
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from core.booking_schedule_engine import (
    BookingScheduleEngine,
    enforce_fixed_service_rules_on_job,
    is_bed_bug_service,
    is_multi_service_booking,
    is_termite_only_service,
    is_termite_service,
    sync_plan_flags_from_service_items,
)
from core.models import JobCard
from core.payment_utils import parse_jobcard_price
from core.payout_engine import calculate_and_apply_payout, is_bed_bug_multi_visit
from core.technician_ledger import heal_stuck_payouts

# Team-reported production IDs (Aug 2026 ledger audit).
REPORTED_BOOKING_IDS = (
    2171, 2252, 2088, 1940, 1925, 2255, 2241, 1965, 2067, 2153, 2122,
)


class Command(BaseCommand):
    help = 'Heal Technician Ledger multi-service / Bed Bugs / Termite / plan-sync gaps.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report changes without writing.',
        )
        parser.add_argument(
            '--ids',
            type=str,
            default='',
            help='Comma-separated booking IDs to heal (default: reported set + global sweeps).',
        )
        parser.add_argument(
            '--reported-only',
            action='store_true',
            help='Only heal --ids / reported booking IDs (skip global Termite/Bed Bugs sweeps).',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        ids = self._parse_ids(options.get('ids') or '')
        reported_only = options['reported_only']

        cancelled = healed_mains = healed_zero = healed_bed = 0
        if not reported_only:
            cancelled = self._cancel_termite_checkups(dry)
            healed_mains = self._heal_termite_mains(dry)
            healed_zero = self._heal_zero_shares(dry)
            healed_bed = self._heal_bed_bug_shares(dry)

        multi = self._heal_multi_service_packages(dry, ids)
        plan_sync = self._heal_plan_sync(dry, ids)
        amount_sync = self._heal_amount_mismatches(dry, ids)
        targeted = self._heal_reported_bookings(dry, ids)

        self.stdout.write(self.style.SUCCESS(
            f"termite_checkups={cancelled}, termite_mains={healed_mains}, "
            f"zero_share={healed_zero}, bed_bug={healed_bed}, "
            f"multi_day1={multi}, plan_sync={plan_sync}, "
            f"amount_sync={amount_sync}, reported={targeted}"
            + (' (dry-run)' if dry else '')
        ))

    def _parse_ids(self, raw: str) -> tuple[int, ...]:
        if not raw.strip():
            return REPORTED_BOOKING_IDS
        out: list[int] = []
        for part in raw.split(','):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
        return tuple(out) or REPORTED_BOOKING_IDS

    def _cancel_termite_checkups(self, dry: bool) -> int:
        qs = JobCard.objects.filter(
            status__in=[JobCard.JobStatus.UPCOMING, JobCard.JobStatus.PENDING],
        ).filter(
            Q(visit_type__icontains='termite')
            | Q(service_type__icontains='termite')
            | Q(source_service__icontains='termite')
        ).filter(
            Q(parent_job__isnull=False)
            | Q(is_followup_visit=True)
            | Q(booking_category=JobCard.BookingCategory.AMC_FOLLOWUP)
            | Q(visit_type__icontains='check')
        )
        count = 0
        for job in qs.iterator():
            text = ' '.join([
                job.service_type or '',
                job.source_service or '',
                job.visit_type or '',
            ])
            if not is_termite_service(text):
                continue
            if (
                not job.parent_job_id
                and not job.is_followup_visit
                and 'check' not in (job.visit_type or '').lower()
            ):
                continue
            count += 1
            if not dry:
                job.status = JobCard.JobStatus.CANCELLED
                job.save(update_fields=['status', 'updated_at'])
        return count

    def _heal_termite_mains(self, dry: bool) -> int:
        qs = JobCard.objects.filter(
            parent_job__isnull=True,
        ).filter(
            Q(service_type__icontains='termite')
            | Q(source_service__icontains='termite')
            | Q(visit_type__icontains='termite')
        ).filter(
            Q(is_amc_main_booking=True)
            | Q(included_in_amc=True)
            | Q(booking_type=JobCard.BookingType.AMC_MAIN)
            | Q(booking_type=JobCard.BookingType.AMC_FOLLOWUP)
            | Q(max_cycle__gt=1)
            | Q(planned_visit_count__gt=1)
            | Q(service_category=JobCard.ServiceCategory.AMC)
        )
        fixed = 0
        for job in qs.iterator():
            primary = (job.source_service or job.service_type or '').strip()
            blob = ' '.join([
                job.service_type or '',
                job.source_service or '',
                job.visit_type or '',
            ])
            if not (is_termite_only_service(primary) or is_termite_only_service(blob)):
                continue
            changed = enforce_fixed_service_rules_on_job(job)
            needs_payout = (
                job.status == JobCard.JobStatus.DONE
                and job.payout_status != JobCard.PayoutStatus.LEGACY_EXEMPT
            )
            package = Decimal(str(job.total_amount or job.price or 0))
            visit = Decimal(str(job.visit_revenue_amount or 0))
            wrong_split = bool(needs_payout and package > 0 and visit < package)
            if not changed and not wrong_split:
                continue
            fixed += 1
            if dry:
                continue
            if changed:
                update_fields = list(dict.fromkeys(changed + ['updated_at']))
                job.sync_booking_category()
                if 'booking_category' not in update_fields:
                    update_fields.append('booking_category')
                job.save(update_fields=update_fields)
            if needs_payout:
                calculate_and_apply_payout(job, force=True)
        return fixed

    def _heal_zero_shares(self, dry: bool) -> int:
        qs = list(
            JobCard.objects.filter(
                status=JobCard.JobStatus.DONE,
                payout_status__in=[
                    JobCard.PayoutStatus.HELD,
                    JobCard.PayoutStatus.PENDING,
                    JobCard.PayoutStatus.NOT_APPLICABLE,
                ],
            ).filter(
                Q(visit_payout_amount__isnull=True)
                | Q(visit_payout_amount__lte=0)
            )[:500]
        )
        if dry:
            return len(qs)
        return heal_stuck_payouts(qs)

    def _heal_bed_bug_shares(self, dry: bool) -> int:
        qs = JobCard.objects.filter(
            status=JobCard.JobStatus.DONE,
        ).filter(
            Q(service_type__icontains='bed')
            | Q(source_service__icontains='bed')
        ).exclude(
            payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT,
        )
        fixed = 0
        for job in qs.iterator():
            if not is_bed_bug_multi_visit(job) and not is_bed_bug_service(job.service_type or ''):
                continue
            if is_multi_service_booking(job):
                continue  # handled in multi heal
            package = Decimal(str(job.total_amount or job.price or 0))
            if package <= 0:
                continue
            expected_visit = (package / Decimal('2')).quantize(Decimal('0.01'))
            expected_tech = (expected_visit * Decimal('0.40')).quantize(Decimal('0.01'))
            current = Decimal(str(job.visit_payout_amount or 0))
            full_wrong = (package * Decimal('0.40')).quantize(Decimal('0.01'))
            if current == expected_tech:
                continue
            if current == full_wrong or current <= 0 or current > expected_tech:
                fixed += 1
                if not dry:
                    changed = enforce_fixed_service_rules_on_job(job)
                    if changed:
                        job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))
                    calculate_and_apply_payout(job, force=True)
        return fixed

    def _heal_multi_service_packages(self, dry: bool, ids: tuple[int, ...]) -> int:
        """
        Backfill missing day-1 children for Done multi-service packages and
        recalculate per-service technician share.
        """
        qs = JobCard.objects.filter(
            parent_job__isnull=True,
            status=JobCard.JobStatus.DONE,
        ).filter(
            Q(pk__in=ids) | Q(visit_type='MULTI SERVICE PACKAGE')
        )
        fixed = 0
        for job in qs.iterator():
            if not is_multi_service_booking(job):
                continue
            day1_before = JobCard.objects.filter(
                parent_job=job, service_cycle=1,
            ).exclude(status=JobCard.JobStatus.CANCELLED).count()
            items = job.service_items or []
            if len(items) < 2 and day1_before >= 2:
                continue
            fixed += 1
            self.stdout.write(
                f"  multi #{job.id}: day1_before={day1_before} items={len(items)}"
            )
            if dry:
                continue
            BookingScheduleEngine.sync_multi_service_day1_children(
                job, completing=True,
            )
            calculate_and_apply_payout(job, force=True)
            for child in JobCard.objects.filter(
                parent_job=job, service_cycle=1,
            ).exclude(status=JobCard.JobStatus.CANCELLED):
                if child.status == JobCard.JobStatus.DONE:
                    calculate_and_apply_payout(child, force=True)
        return fixed

    def _heal_plan_sync(self, dry: bool, ids: tuple[int, ...]) -> int:
        """Clear stale AMC flags when service_items are One-Time (#1965, #2153)."""
        qs = JobCard.objects.filter(pk__in=ids, parent_job__isnull=True)
        fixed = 0
        for job in qs.iterator():
            changed = sync_plan_flags_from_service_items(job)
            if not changed:
                continue
            fixed += 1
            self.stdout.write(f"  plan-sync #{job.id}: {changed}")
            if dry:
                continue
            update_fields = list(dict.fromkeys(changed + ['updated_at']))
            job.sync_booking_category()
            if 'booking_category' not in update_fields:
                update_fields.append('booking_category')
            job.save(update_fields=update_fields)
            if job.status == JobCard.JobStatus.DONE:
                calculate_and_apply_payout(job, force=True)
                for child in JobCard.objects.filter(parent_job=job).exclude(
                    status=JobCard.JobStatus.CANCELLED,
                ):
                    if child.status == JobCard.JobStatus.DONE:
                        calculate_and_apply_payout(child, force=True)
        return fixed

    def _heal_amount_mismatches(self, dry: bool, ids: tuple[int, ...]) -> int:
        """
        Align parent price/total with sum of service_items when items look correct
        (#2255: booking 2500 vs ledger 1500).
        """
        fixed = 0
        for job in JobCard.objects.filter(pk__in=ids, parent_job__isnull=True):
            items = job.service_items if isinstance(job.service_items, list) else []
            if not items:
                continue
            items_sum = sum(parse_jobcard_price(i.get('amount')) for i in items)
            if items_sum <= 0:
                continue
            price = parse_jobcard_price(job.price)
            total = Decimal(str(job.total_amount or 0))
            if price == items_sum and total == items_sum:
                continue
            # Prefer items sum when it differs from stale parent price.
            if abs(price - items_sum) < Decimal('0.01') and abs(total - items_sum) < Decimal('0.01'):
                continue
            fixed += 1
            self.stdout.write(
                f"  amount #{job.id}: price={price} total={total} items_sum={items_sum}"
            )
            if dry:
                continue
            job.price = str(items_sum)
            job.total_amount = items_sum
            job.save(update_fields=['price', 'total_amount', 'updated_at'])
            if job.status == JobCard.JobStatus.DONE:
                if is_multi_service_booking(job):
                    BookingScheduleEngine.sync_multi_service_day1_children(
                        job, completing=True,
                    )
                    calculate_and_apply_payout(job, force=True)
                    for child in JobCard.objects.filter(
                        parent_job=job, service_cycle=1,
                    ).exclude(status=JobCard.JobStatus.CANCELLED):
                        # Refresh child line amount from items
                        for item in items:
                            if str(item.get('service') or '').strip() == (
                                child.source_service or child.service_type or ''
                            ).strip():
                                amt = parse_jobcard_price(item.get('amount'))
                                if amt > 0:
                                    child.price = str(amt)
                                    child.total_amount = amt
                                    child.save(update_fields=[
                                        'price', 'total_amount', 'updated_at',
                                    ])
                        if child.status == JobCard.JobStatus.DONE:
                            calculate_and_apply_payout(child, force=True)
                else:
                    calculate_and_apply_payout(job, force=True)
        return fixed

    def _heal_reported_bookings(self, dry: bool, ids: tuple[int, ...]) -> int:
        """Final pass: force payout recalc on reported Done bookings + day-1 kids."""
        fixed = 0
        for job in JobCard.objects.filter(pk__in=ids).select_related('parent_job'):
            # Fix polluted child service names under Bed Bugs parents (#2252/#2253).
            if job.parent_job_id:
                parent = job.parent_job
                if parent and is_bed_bug_service(parent.service_type or '') and not (
                    is_multi_service_booking(parent)
                ):
                    if not is_bed_bug_service(job.service_type or ''):
                        fixed += 1
                        self.stdout.write(
                            f"  rename child #{job.id} → Bed Bugs "
                            f"(was {job.service_type!r})"
                        )
                        if not dry:
                            job.service_type = 'Bed Bugs'
                            job.source_service = 'Bed Bugs'
                            job.service_items = [
                                {
                                    'service': 'Bed Bugs',
                                    'plan': (job.service_items or [{}])[0].get('plan', '')
                                    if job.service_items else '',
                                    'area': job.bhk_size or '',
                                    'amount': float(parse_jobcard_price(job.price) or 0),
                                }
                            ]
                            job.save(update_fields=[
                                'service_type', 'source_service', 'service_items', 'updated_at',
                            ])
                continue

            if job.status != JobCard.JobStatus.DONE:
                # Still sync plan flags for open One-Time edits.
                if dry:
                    continue
                changed = sync_plan_flags_from_service_items(job)
                if changed:
                    job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))
                    fixed += 1
                continue

            fixed += 1
            if dry:
                self.stdout.write(f"  recalc #{job.id}")
                continue
            if is_multi_service_booking(job):
                BookingScheduleEngine.sync_multi_service_day1_children(
                    job, completing=True,
                )
            calculate_and_apply_payout(job, force=True)
            for child in JobCard.objects.filter(parent_job=job).exclude(
                status=JobCard.JobStatus.CANCELLED,
            ):
                if child.status == JobCard.JobStatus.DONE:
                    calculate_and_apply_payout(child, force=True)
        return fixed
