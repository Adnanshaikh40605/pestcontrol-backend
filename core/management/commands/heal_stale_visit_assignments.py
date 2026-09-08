"""
Heal visits and participations left on a previously assigned technician.

Before reassignment went through one shared path, changing a booking's
technician did not follow through to its per-service / follow-up visits, so the
Technician Ledger kept showing the old technician.

  python manage.py heal_stale_visit_assignments --dry-run
  python manage.py heal_stale_visit_assignments
  python manage.py heal_stale_visit_assignments --ids 2645 2538
"""
from django.core.management.base import BaseCommand
from django.db.models import F

from core.models import JobCard, JobCardTechnicianParticipation
from core.payout_engine import (
    enforce_single_lead_participation,
    purge_stale_revenue_share_earnings,
    reassign_job_technician,
)

OPEN_VISIT_EXCLUDED_STATUSES = [JobCard.JobStatus.DONE, JobCard.JobStatus.CANCELLED]
LOCKED_PAYOUT_STATUSES = [JobCard.PayoutStatus.APPROVED, JobCard.PayoutStatus.PAID]


class Command(BaseCommand):
    help = 'Point open child visits and lead participations at the current booking technician.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--ids',
            type=int,
            nargs='*',
            default=[],
            help='Only heal these booking ids (parent bookings).',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        ids = options['ids']

        moved_visits = self._heal_child_visits(dry, ids)
        fixed_leads = self._heal_lead_participations(dry, ids)

        summary = f'visits moved: {moved_visits} · stale lead rows: {fixed_leads}'
        self.stdout.write(
            self.style.WARNING(f'dry-run · {summary}') if dry
            else self.style.SUCCESS(summary)
        )

    def _heal_child_visits(self, dry: bool, ids: list[int]) -> int:
        parents = JobCard.objects.filter(
            technician__isnull=False,
            follow_up_jobs__isnull=False,
        ).distinct()
        if ids:
            parents = parents.filter(id__in=ids)

        moved = 0
        # Pooled connections reject server-side cursors, so read the page fully.
        for parent in list(parents.select_related('technician')):
            stale = (
                JobCard.objects.filter(parent_job=parent, technician__isnull=False)
                .exclude(technician_id=parent.technician_id)
                .exclude(status__in=OPEN_VISIT_EXCLUDED_STATUSES)
                .exclude(payout_status__in=LOCKED_PAYOUT_STATUSES)
                .select_related('technician')
            )
            for child in list(stale):
                self.stdout.write(
                    f"visit #{child.id} ({child.service_type}) "
                    f"{child.technician.name!r} → {parent.technician.name!r} "
                    f"[booking #{parent.id}]"
                )
                if not dry:
                    reassign_job_technician(child, parent.technician)
                moved += 1
        return moved

    def _heal_lead_participations(self, dry: bool, ids: list[int]) -> int:
        rows = JobCardTechnicianParticipation.objects.filter(
            role=JobCardTechnicianParticipation.Role.LEAD,
            jobcard__technician__isnull=False,
        ).exclude(technician_id=F('jobcard__technician_id'))
        if ids:
            rows = rows.filter(jobcard_id__in=ids)

        fixed = 0
        for row in list(rows.select_related('jobcard', 'technician')):
            self.stdout.write(
                f"lead row on job #{row.jobcard_id}: {row.technician.name!r} "
                f"is not the assigned technician"
            )
            if not dry:
                enforce_single_lead_participation(row.jobcard)
                purge_stale_revenue_share_earnings(row.jobcard)
            fixed += 1
        return fixed
