"""
Backfill Bed Bugs 2-visit packages on already-created bookings.

Usage:
  python manage.py heal_bed_bug_packages --dry-run
  python manage.py heal_bed_bug_packages
"""
from django.core.management.base import BaseCommand

from core.booking_schedule_engine import heal_all_bed_bug_packages
from core.models import JobCard
from core.payout_engine import calculate_and_apply_payout


def heal_completed_bed_bug_followups() -> tuple[int, int]:
    """Normalize old cycle-2 Bed Bugs rows and force payout recompute."""
    fixed = 0
    recalculated = 0
    qs = JobCard.objects.filter(
        status=JobCard.JobStatus.DONE,
        service_cycle__gte=2,
    ).filter(
        service_type__icontains='bed',
    ).exclude(
        payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT,
    )
    from core.booking_schedule_engine import enforce_fixed_service_rules_on_job

    for job in qs.iterator():
        changed = enforce_fixed_service_rules_on_job(job)
        if changed:
            fixed += 1
            job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))
        # Force-recalculate so visit_revenue/pool/payout are never stuck at zero.
        result = calculate_and_apply_payout(job, force=True)
        if not result.skipped:
            recalculated += 1
    return fixed, recalculated


class Command(BaseCommand):
    help = 'Lock existing Bed Bugs bookings to 2 visits and create the missing 15-day follow-up.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Count bookings that need healing without writing.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        result = heal_all_bed_bug_packages(dry=dry)
        suffix = ' (dry-run)' if dry else ''
        msg = (
            f"scanned={result['scanned']} healed={result['healed']} "
            f"created_visits={result['created_visits']}"
        )
        if dry:
            self.stdout.write(self.style.SUCCESS(f"{msg}{suffix}"))
            return

        fixed, recalculated = heal_completed_bed_bug_followups()
        self.stdout.write(self.style.SUCCESS(
            f"{msg} followup_flags_fixed={fixed} payouts_recalculated={recalculated}"
        ))
