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

from datetime import date, datetime, time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.booking_schedule_engine import (
    BookingScheduleEngine,
    enforce_fixed_service_rules_on_job,
    heal_all_bed_bug_packages,
    heal_bed_bug_package,
    is_bed_bug_service,
    is_multi_service_booking,
    is_termite_only_service,
    is_termite_service,
    job_includes_bed_bugs,
    sync_plan_flags_from_service_items,
)
from core.models import JobCard
from core.payment_utils import parse_jobcard_price
from core.payout_engine import (
    calculate_and_apply_payout,
    is_amc_economics,
    is_bed_bug_multi_visit,
    service_line_package_amount,
)
from core.technician_ledger import heal_stuck_payouts, job_needs_payout_heal

# Team-reported production IDs (Technician Ledger audits).
REPORTED_BOOKING_IDS = (
    2171, 2252, 2088, 1940, 1925, 2255, 2241, 1965, 2067, 2153, 2122,
    2085, 1928, 1895, 2034, 2213, 1909,
    1934, 2147, 2103,
    # Aug 2026 — Rajendra / Sohail ledger: old 2nd services + multi-service doubles
    1243, 1145, 2258, 1176, 2069, 2389, 2159, 1151, 1921, 2550, 2540,
    2558, 2618, 2566, 1415, 1817, 2211, 2548, 2388, 2549,
)

# Old follow-up / 2nd service rows that were force-migrated into unsettled payables.
# Restore to legacy_exempt so they stay "Old record" and do not pay again.
OLD_FOLLOWUP_LEGACY_IDS = (
    1145, 1151, 1176, 1243, 1415, 1921, 2069, 2159, 2558, 2566,
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
        parser.add_argument(
            '--since',
            type=str,
            default='',
            help='Heal all bookings on/after this date (YYYY-MM-DD), e.g. 2026-08-01.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        since = self._parse_since(options.get('since') or '')
        reported_only = options['reported_only']
        ids = self._parse_ids(options.get('ids') or '')

        if since:
            ids = self._ids_since(since)
            self.stdout.write(
                f"Since {since.isoformat()}: {len(ids)} booking IDs in window "
                f"(+ parents/children will be included by heal steps)."
            )
            # Date-scoped full heal — do not expand into unrelated historical IDs.
            reported_only = False

        cancelled = healed_mains = healed_zero = healed_bed = 0
        bed_packages = {'scanned': 0, 'healed': 0, 'created_visits': 0}
        since_fixed = 0

        if since:
            since_fixed = self._heal_window_since(dry, since, ids)
        elif not reported_only:
            cancelled = self._cancel_termite_checkups(dry)
            healed_mains = self._heal_termite_mains(dry)
            healed_zero = self._heal_zero_shares(dry)
            bed_packages = heal_all_bed_bug_packages(dry=dry)
            self.stdout.write(
                '  bed-bug packages: '
                f"scanned={bed_packages['scanned']} "
                f"healed={bed_packages['healed']} "
                f"created_visits={bed_packages['created_visits']}"
                + (' (dry-run)' if dry else '')
            )
            healed_bed = self._heal_bed_bug_shares(dry)

        multi = self._heal_multi_service_packages(dry, ids, ids_only=bool(since) or reported_only)
        plan_sync = self._heal_plan_sync(dry, ids)
        amount_sync = self._heal_amount_mismatches(dry, ids)
        amc_full = 0 if (reported_only and not since) else self._heal_amc_full_package_visits(
            dry, ids if since else None,
        )
        legacy = self._restore_old_followups_to_legacy(dry, ids)
        multi_lines = self._heal_multi_service_line_amounts(dry, ids)
        dupes = self._cancel_duplicate_bed_bug_followups(dry, ids)
        complaints = self._zero_complaint_payouts(dry, ids)
        targeted = self._heal_reported_bookings(dry, ids)

        self.stdout.write(self.style.SUCCESS(
            f"since_window={since_fixed}, "
            f"termite_checkups={cancelled}, termite_mains={healed_mains}, "
            f"zero_share={healed_zero}, "
            f"bed_bug_packages={bed_packages['healed']}/"
            f"{bed_packages['created_visits']}, "
            f"bed_bug_payout={healed_bed}, "
            f"multi_day1={multi}, plan_sync={plan_sync}, "
            f"amount_sync={amount_sync}, amc_full={amc_full}, "
            f"legacy_followups={legacy}, multi_lines={multi_lines}, "
            f"dup_bedbug={dupes}, complaints={complaints}, reported={targeted}"
            + (' (dry-run)' if dry else '')
        ))

    def _parse_since(self, raw: str):
        raw = (raw or '').strip()
        if not raw:
            return None
        parsed = parse_date(raw)
        if not parsed:
            raise SystemExit(f'Invalid --since date: {raw!r} (use YYYY-MM-DD)')
        return parsed

    def _ids_since(self, since: date) -> tuple[int, ...]:
        """All job IDs whose schedule / completion / create date is on or after since."""
        start = timezone.make_aware(datetime.combine(since, time.min))
        qs = JobCard.objects.filter(
            Q(schedule_datetime__gte=start)
            | Q(completed_at__gte=start)
            | Q(created_at__gte=start)
        ).exclude(status=JobCard.JobStatus.CANCELLED)
        ids = list(qs.values_list('id', flat=True))
        # Include parents of children in the window so package shells heal too.
        parent_ids = list(
            JobCard.objects.filter(pk__in=ids, parent_job_id__isnull=False)
            .values_list('parent_job_id', flat=True)
            .distinct()
        )
        child_ids = list(
            JobCard.objects.filter(parent_job_id__in=ids)
            .exclude(status=JobCard.JobStatus.CANCELLED)
            .values_list('id', flat=True)
        )
        return tuple(sorted(set(ids) | set(parent_ids) | set(child_ids)))

    def _heal_window_since(self, dry: bool, since: date, ids: tuple[int, ...]) -> int:
        """
        Full pass for every booking in the date window:
        - Bed Bugs 2-visit lock + flags
        - Multi-service day-1 split
        - Wrong / stuck Tech 40% recalculation
        - Follow-up price zeroing via enforce_fixed_service_rules
        """
        fixed = 0
        roots_seen: set[int] = set()
        qs = (
            JobCard.objects.filter(pk__in=ids)
            .select_related('parent_job')
            .order_by('id')
        )
        for job in qs.iterator():
            root = job.parent_job or job
            if root.id not in roots_seen and job_includes_bed_bugs(root):
                roots_seen.add(root.id)
                if dry:
                    fixed += 1
                    self.stdout.write(f"  since-bedbug-package #{root.id}")
                else:
                    created = heal_bed_bug_package(root)
                    if created:
                        fixed += 1
                        self.stdout.write(
                            f"  since-bedbug-package #{root.id} +{len(created)} visits"
                        )

            changed = enforce_fixed_service_rules_on_job(job)
            if changed:
                fixed += 1
                self.stdout.write(f"  since-flags #{job.id}: {changed}")
                if not dry:
                    job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))

            if (
                not dry
                and job.status == JobCard.JobStatus.DONE
                and job.payout_status != JobCard.PayoutStatus.LEGACY_EXEMPT
                and job_needs_payout_heal(job)
            ):
                if is_multi_service_booking(job) and not job.parent_job_id:
                    BookingScheduleEngine.sync_multi_service_day1_children(
                        job, completing=True,
                    )
                calculate_and_apply_payout(job, force=True)
                fixed += 1
                self.stdout.write(f"  since-payout #{job.id}")
            elif dry and job.status == JobCard.JobStatus.DONE and job_needs_payout_heal(job):
                if job.payout_status != JobCard.PayoutStatus.LEGACY_EXEMPT:
                    fixed += 1
                    self.stdout.write(f"  since-payout #{job.id} (would recalc)")

        # Batch heal stuck payouts in the window (non-legacy Done).
        done_jobs = list(
            JobCard.objects.filter(
                pk__in=ids,
                status=JobCard.JobStatus.DONE,
            ).exclude(payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT)
        )
        if dry:
            need = sum(1 for j in done_jobs if job_needs_payout_heal(j))
            self.stdout.write(f"  since-stuck-candidates={need}")
        else:
            healed = heal_stuck_payouts(done_jobs)
            fixed += healed
            self.stdout.write(f"  since-stuck-healed={healed}")
        return fixed

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

    def _heal_amc_full_package_visits(self, dry: bool, ids: tuple[int, ...] | None = None) -> int:
        """
        AMC Done visits that stored full package × 40% instead of (package ÷ N) × 40%.
        Example: #1934 AMC 3 Services ₹2500 → must be ₹333.33 tech, not ₹1000.
        """
        qs = JobCard.objects.filter(
            status=JobCard.JobStatus.DONE,
        ).filter(
            Q(service_category=JobCard.ServiceCategory.AMC)
            | Q(is_amc_main_booking=True)
            | Q(included_in_amc=True)
            | Q(is_followup_visit=True)
            | Q(booking_type=JobCard.BookingType.AMC_MAIN)
            | Q(booking_type=JobCard.BookingType.AMC_FOLLOWUP)
            | Q(max_cycle__gt=1)
            | Q(planned_visit_count__gt=1)
        ).exclude(
            payout_status__in=[
                JobCard.PayoutStatus.APPROVED,
                JobCard.PayoutStatus.PAID,
                JobCard.PayoutStatus.CANCELLED,
                JobCard.PayoutStatus.LEGACY_EXEMPT,
            ],
        )
        if ids is not None:
            qs = qs.filter(pk__in=ids)
        fixed = 0
        for job in qs.iterator():
            if is_bed_bug_multi_visit(job):
                continue
            if not is_amc_economics(job):
                continue
            if not job_needs_payout_heal(job):
                continue
            package = service_line_package_amount(job)
            if package <= 0:
                continue
            fixed += 1
            self.stdout.write(
                f"  amc-fix #{job.id}: rev={job.visit_revenue_amount} "
                f"pay={job.visit_payout_amount} max={job.max_cycle} "
                f"planned={job.planned_visit_count}"
            )
            if dry:
                continue
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

    def _heal_multi_service_packages(self, dry: bool, ids: tuple[int, ...], *, ids_only: bool = False) -> int:
        """
        Backfill missing day-1 children for Done multi-service packages and
        recalculate per-service technician share.
        """
        root_ids = set(ids)
        for job in JobCard.objects.filter(pk__in=ids).exclude(parent_job_id=None):
            root_ids.add(job.parent_job_id)
        qs = JobCard.objects.filter(
            parent_job__isnull=True,
            status=JobCard.JobStatus.DONE,
        )
        if ids_only:
            qs = qs.filter(pk__in=root_ids)
        else:
            qs = qs.filter(Q(pk__in=root_ids) | Q(visit_type='MULTI SERVICE PACKAGE'))
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

            # Clear false follow-up flag on Bed Bugs roots (e.g. #2034).
            if (
                not job.parent_job_id
                and is_bed_bug_service(job.service_type or job.source_service or '')
                and (job.is_followup_visit or job.included_in_amc)
                and (job.service_cycle or 1) <= 1
            ):
                job.is_followup_visit = False
                job.included_in_amc = False
                if not dry:
                    job.save(update_fields=[
                        'is_followup_visit', 'included_in_amc', 'updated_at',
                    ])
                fixed += 1

            if job.status != JobCard.JobStatus.DONE:
                # Still sync plan flags for open One-Time edits.
                if dry:
                    continue
                changed = sync_plan_flags_from_service_items(job)
                if changed:
                    job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))
                    fixed += 1
                continue

            if job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT:
                continue
            if job.id in OLD_FOLLOWUP_LEGACY_IDS:
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
                    if child.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT:
                        continue
                    if child.id in OLD_FOLLOWUP_LEGACY_IDS:
                        continue
                    calculate_and_apply_payout(child, force=True)
        return fixed

    def _restore_old_followups_to_legacy(self, dry: bool, ids: tuple[int, ...]) -> int:
        """
        Mark reported old 2nd/3rd service visits as legacy_exempt with ₹0 ledger.
        Staff want these as Old record — not unsettled payables after auto-heal migrated them.
        """
        target = set(OLD_FOLLOWUP_LEGACY_IDS) | {
            i for i in ids
            if i in OLD_FOLLOWUP_LEGACY_IDS
        }
        fixed = 0
        for job in JobCard.objects.filter(pk__in=target):
            cycle = job.service_cycle or 1
            is_followup = (
                cycle > 1
                or job.is_followup_visit
                or job.is_service_call
                or job.included_in_amc
                or job.booking_type in (
                    JobCard.BookingType.AMC_FOLLOWUP,
                    JobCard.BookingType.SERVICE_CALL,
                )
            )
            if not is_followup and cycle <= 1:
                continue
            already = (
                job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT
                and Decimal(str(job.visit_payout_amount or 0)) <= 0
                and Decimal(str(job.visit_revenue_amount or 0)) <= 0
            )
            if already:
                continue
            fixed += 1
            self.stdout.write(
                f"  legacy-followup #{job.id} cycle={cycle} "
                f"was_pay={job.visit_payout_amount} → Old record"
            )
            if dry:
                continue
            job.price = '0'
            job.total_amount = Decimal('0.00')
            job.paid_amount = Decimal('0.00')
            job.pending_amount = Decimal('0.00')
            job.visit_revenue_amount = Decimal('0.00')
            job.technician_pool_amount = Decimal('0.00')
            job.company_share_amount = Decimal('0.00')
            job.visit_payout_amount = Decimal('0.00')
            job.payout_status = JobCard.PayoutStatus.LEGACY_EXEMPT
            job.is_followup_visit = True
            if not job.is_service_call and cycle > 1:
                job.is_service_call = True
            job.save(update_fields=[
                'price', 'total_amount', 'paid_amount', 'pending_amount',
                'visit_revenue_amount', 'technician_pool_amount', 'company_share_amount',
                'visit_payout_amount', 'payout_status', 'is_followup_visit',
                'is_service_call', 'updated_at',
            ])
            # Clear partner earnings so settlement cannot pick them up again.
            from partner.models import PartnerEarning
            PartnerEarning.objects.filter(job=job).delete()
            for part in job.technician_participations.all():
                part.payout_amount_snapshot = Decimal('0.00')
                part.save(update_fields=['payout_amount_snapshot', 'updated_at'])
        return fixed

    def _heal_multi_service_line_amounts(self, dry: bool, ids: tuple[int, ...]) -> int:
        """
        Day-1 children must carry their own line amount — never the full shell total.
        Fixes Cockroach+Rodent both showing the same ₹2500 / same tech share (#2389, #2550).
        """
        roots = set()
        for job in JobCard.objects.filter(pk__in=ids).select_related('parent_job'):
            roots.add(job.parent_job_id or job.id)
        fixed = 0
        for root in JobCard.objects.filter(pk__in=roots, parent_job__isnull=True):
            if not is_multi_service_booking(root):
                continue
            items = root.service_items if isinstance(root.service_items, list) else []
            if len(items) < 2:
                continue
            by_service = {
                str((item or {}).get('service') or '').strip(): parse_jobcard_price(
                    (item or {}).get('amount')
                )
                for item in items
                if str((item or {}).get('service') or '').strip()
            }
            day1 = JobCard.objects.filter(parent_job=root, service_cycle=1).exclude(
                status=JobCard.JobStatus.CANCELLED,
            )
            changed_any = False
            for child in day1:
                key = (child.source_service or child.service_type or '').strip()
                amt = by_service.get(key)
                if amt is None:
                    continue
                cur = parse_jobcard_price(child.price)
                tot = Decimal(str(child.total_amount or 0))
                items_sum = sum(by_service.values())
                # Parent line sometimes stores ₹0 while the child already has the
                # correct line price (Cafe Holiday Rodent #2550). Keep child amount.
                if amt <= 0 and cur > 0 and (items_sum <= 0 or cur < items_sum):
                    amt = cur
                if amt < 0:
                    continue
                full_tech = (items_sum * Decimal('0.40')).quantize(Decimal('0.01')) if items_sum > 0 else Decimal('0.00')
                line_tech = (amt * Decimal('0.40')).quantize(Decimal('0.01')) if amt > 0 else Decimal('0.00')
                cur_pay = Decimal(str(child.visit_payout_amount or 0))
                cur_rev = Decimal(str(child.visit_revenue_amount or 0))
                bad = (
                    cur != amt
                    or tot != amt
                    or (items_sum > 0 and cur >= items_sum and len(by_service) > 1)
                    or (amt > 0 and cur_rev > amt)
                    or (full_tech > 0 and cur_pay >= full_tech and line_tech < full_tech)
                )
                if not bad:
                    continue
                fixed += 1
                changed_any = True
                self.stdout.write(
                    f"  multi-line #{child.id} ({key}): price {cur}/{tot} → {amt}"
                )
                if dry:
                    continue
                child.price = str(amt)
                child.total_amount = amt
                child.service_items = [
                    item for item in items
                    if str((item or {}).get('service') or '').strip() == key
                ] or [{
                    'service': key,
                    'plan': 'One Time Service',
                    'area': child.bhk_size or '',
                    'amount': float(amt),
                }]
                # Keep matching parent line amount in sync when child had the truth.
                if by_service.get(key, Decimal('0')) <= 0 and amt > 0:
                    for item in items:
                        if str((item or {}).get('service') or '').strip() == key:
                            item['amount'] = float(amt)
                    root.service_items = items
                    root.save(update_fields=['service_items', 'updated_at'])
                    by_service[key] = amt
                child.source_service = key
                child.save(update_fields=[
                    'price', 'total_amount', 'service_items', 'source_service', 'updated_at',
                ])
                if child.status == JobCard.JobStatus.DONE:
                    calculate_and_apply_payout(child, force=True)
            if changed_any and not dry:
                calculate_and_apply_payout(root, force=True)
        return fixed

    def _cancel_duplicate_bed_bug_followups(self, dry: bool, ids: tuple[int, ...]) -> int:
        """Cancel extra cycle-2 Bed Bugs rows when a parent already has one active follow-up."""
        roots = set()
        for job in JobCard.objects.filter(pk__in=ids).select_related('parent_job'):
            root = job.parent_job_id or job.id
            roots.add(root)
        fixed = 0
        for root_id in roots:
            kids = list(
                JobCard.objects.filter(
                    parent_job_id=root_id,
                    service_cycle=2,
                ).exclude(status=JobCard.JobStatus.CANCELLED).order_by('id')
            )
            if len(kids) < 2:
                continue
            # Keep the earliest Done, else earliest Upcoming.
            keep = next((k for k in kids if k.status == JobCard.JobStatus.DONE), kids[0])
            for kid in kids:
                if kid.id == keep.id:
                    continue
                fixed += 1
                self.stdout.write(
                    f"  dup-bedbug cancel #{kid.id} (keep #{keep.id} under parent #{root_id})"
                )
                if dry:
                    continue
                kid.status = JobCard.JobStatus.CANCELLED
                kid.visit_revenue_amount = Decimal('0.00')
                kid.technician_pool_amount = Decimal('0.00')
                kid.company_share_amount = Decimal('0.00')
                kid.visit_payout_amount = Decimal('0.00')
                kid.payout_status = JobCard.PayoutStatus.CANCELLED
                kid.save(update_fields=[
                    'status', 'visit_revenue_amount', 'technician_pool_amount',
                    'company_share_amount', 'visit_payout_amount', 'payout_status',
                    'updated_at',
                ])
        return fixed

    def _zero_complaint_payouts(self, dry: bool, ids: tuple[int, ...]) -> int:
        fixed = 0
        for job in JobCard.objects.filter(pk__in=ids):
            if not (
                job.is_complaint_call
                or job.booking_type == JobCard.BookingType.COMPLAINT_CALL
            ):
                continue
            if (
                job.payout_status == JobCard.PayoutStatus.NOT_APPLICABLE
                and Decimal(str(job.visit_payout_amount or 0)) <= 0
            ):
                continue
            fixed += 1
            self.stdout.write(f"  complaint-zero #{job.id}")
            if dry:
                continue
            calculate_and_apply_payout(job, force=True)
        return fixed
