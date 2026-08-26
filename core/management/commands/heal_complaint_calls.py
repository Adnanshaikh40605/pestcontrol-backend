"""Heal historical complaint calls that were treated as new packages."""
from django.core.management.base import BaseCommand

from core.complaint_service import heal_complaint_jobs


class Command(BaseCommand):
    help = (
        'Link complaint calls to original bookings, force Free (Complaint) single-service '
        'constraints, and cancel spurious Bed Bugs/AMC follow-ups spawned from complaints.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report changes without writing to the database',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Optional max complaint rows to process',
        )

    def handle(self, *args, **options):
        dry_run = bool(options['dry_run'])
        limit = options.get('limit')
        result = heal_complaint_jobs(dry_run=dry_run, limit=limit)
        self.stdout.write(self.style.SUCCESS(
            f"complaints={result['complaint_rows']} normalized={result['normalized']} "
            f"linked={result['linked_parents']} cancelled_followups={result['cancelled_followups']} "
            f"dry_run={result['dry_run']}"
        ))
        if result['cancelled_ids']:
            self.stdout.write(f"cancelled_ids={result['cancelled_ids']}")
        for row in result['details'][:30]:
            self.stdout.write(
                f"  #{row['complaint_id']} parent={row['parent_id']} "
                f"fields={row['changed_fields']} cancelled={row['cancelled_followups']}"
            )
