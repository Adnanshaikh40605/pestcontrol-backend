"""
Cleanup / heal production data for technician_ledger_fixes.md gaps.

- Cancel auto-generated Termite checkup / AMC-followup children (Termite = One-Time only)
- Rewrite Termite-only mains still flagged as AMC (booking_type / max_cycle / payout)
- Force-recalculate Bed Bugs and stuck ₹0 Tech-share Done jobs

Usage:
  python manage.py cleanup_technician_ledger_data --dry-run
  python manage.py cleanup_technician_ledger_data
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from core.booking_schedule_engine import (
    enforce_fixed_service_rules_on_job,
    is_bed_bug_service,
    is_termite_only_service,
    is_termite_service,
)
from core.models import JobCard
from core.payout_engine import calculate_and_apply_payout, is_bed_bug_multi_visit
from core.technician_ledger import heal_stuck_payouts


class Command(BaseCommand):
    help = 'Cancel old Termite checkup chains and heal Bed Bugs / ₹0 tech-share payouts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report changes without writing.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        cancelled = self._cancel_termite_checkups(dry)
        healed_mains = self._heal_termite_mains(dry)
        healed_zero = self._heal_zero_shares(dry)
        healed_bed = self._heal_bed_bug_shares(dry)
        self.stdout.write(self.style.SUCCESS(
            f"Termite checkups cancelled={cancelled}, "
            f"termite mains healed={healed_mains}, "
            f"zero-share healed={healed_zero}, "
            f"bed-bug recalculated={healed_bed}"
            + (' (dry-run)' if dry else '')
        ))

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
            # Keep a standalone one-time Termite main (no parent) that is not a checkup.
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
        """
        Legacy Termite mains were saved as AMC Main + max_cycle=5 with checkup children.
        Rewrite them to One-Time and recalculate Done payouts (full package × 40%).
        """
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
            # Legacy AMC split: visit revenue was package ÷ 5 instead of full one-time.
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
            package = Decimal(str(job.total_amount or job.price or 0))
            if package <= 0:
                continue
            expected_visit = (package / Decimal('2')).quantize(Decimal('0.01'))
            expected_tech = (expected_visit * Decimal('0.40')).quantize(Decimal('0.01'))
            current = Decimal(str(job.visit_payout_amount or 0))
            # Wrong if they got full-package 40% instead of half
            full_wrong = (package * Decimal('0.40')).quantize(Decimal('0.01'))
            if current == expected_tech:
                continue
            if current == full_wrong or current <= 0 or current > expected_tech:
                fixed += 1
                if not dry:
                    calculate_and_apply_payout(job, force=True)
        return fixed
