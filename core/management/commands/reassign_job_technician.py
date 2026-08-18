"""
Move a visit onto the technician who actually did the work and rebuild ledger.

Example (VAMA #2260 Cockroach was overwritten to Mustafa; Akshay did it):
  python manage.py reassign_job_technician --job 2260 --technician-id 5
  python manage.py reassign_job_technician --job 2260 --technician-id 5 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError

from core.models import JobCard, Technician
from core.payout_engine import reassign_job_technician


class Command(BaseCommand):
    help = 'Reassign a booking/visit to a technician and recalculate Technician Ledger.'

    def add_arguments(self, parser):
        parser.add_argument('--job', type=int, required=True, help='JobCard id (e.g. 2260).')
        parser.add_argument('--technician-id', type=int, required=True, help='Technician id.')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        job_id = options['job']
        tech_id = options['technician_id']
        dry = options['dry_run']
        try:
            job = JobCard.objects.select_related('technician', 'parent_job').get(pk=job_id)
        except JobCard.DoesNotExist as exc:
            raise CommandError(f'Job {job_id} not found') from exc
        try:
            tech = Technician.objects.get(pk=tech_id)
        except Technician.DoesNotExist as exc:
            raise CommandError(f'Technician {tech_id} not found') from exc

        self.stdout.write(
            f"job={job.id} {job.service_type} parent={job.parent_job_id} "
            f"status={job.status} current={getattr(job.technician, 'name', None)!r} "
            f"→ {tech.name!r}"
        )
        if dry:
            self.stdout.write(self.style.WARNING('dry-run: no write'))
            return
        result = reassign_job_technician(job, tech)
        self.stdout.write(self.style.SUCCESS(
            f"reassigned {result['previous_technician_name']!r} → {result['technician_name']!r} "
            f"payout={result['payout_status']}"
        ))
