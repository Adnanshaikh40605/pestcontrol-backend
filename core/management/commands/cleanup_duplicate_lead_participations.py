"""
Remove stale LEAD participation rows so each visit maps to one technician ledger.

Run after deploy or when staff report duplicate ledger entries:
  python manage.py cleanup_duplicate_lead_participations
  python manage.py cleanup_duplicate_lead_participations --dry-run
"""
from django.core.management.base import BaseCommand

from core.models import JobCard, JobCardTechnicianParticipation
from core.payout_engine import enforce_single_lead_participation


class Command(BaseCommand):
    help = 'Delete extra LEAD rows that are not the assigned JobCard.technician.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry = options['dry_run']
        lead = JobCardTechnicianParticipation.Role.LEAD

        job_ids = JobCardTechnicianParticipation.objects.filter(
            role=lead,
        ).values_list('jobcard_id', flat=True).distinct()

        healed = 0
        removed_total = 0
        for job in JobCard.objects.filter(id__in=job_ids).select_related('technician'):
            lead_rows = job.technician_participations.filter(role=lead)
            if lead_rows.count() <= 1 and (
                not job.technician_id
                or lead_rows.filter(technician_id=job.technician_id).exists()
            ):
                continue

            if dry:
                names = list(lead_rows.values_list('technician__name', flat=True))
                self.stdout.write(
                    f"job={job.id} assigned={getattr(job.technician, 'name', None)!r} "
                    f"leads={names!r}"
                )
                continue

            removed = enforce_single_lead_participation(job)
            if removed:
                healed += 1
                removed_total += removed
                self.stdout.write(
                    self.style.SUCCESS(
                        f"job={job.id} removed {removed} stale lead row(s) "
                        f"→ {getattr(job.technician, 'name', None)!r}"
                    )
                )

        if dry:
            self.stdout.write(self.style.WARNING('dry-run: no writes'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"healed {healed} job(s), removed {removed_total} stale lead row(s)"
                )
            )
