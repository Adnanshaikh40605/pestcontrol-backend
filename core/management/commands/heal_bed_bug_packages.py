"""
Backfill Bed Bugs 2-visit packages on already-created bookings.

Usage:
  python manage.py heal_bed_bug_packages --dry-run
  python manage.py heal_bed_bug_packages
"""
from django.core.management.base import BaseCommand

from core.booking_schedule_engine import heal_all_bed_bug_packages


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
        self.stdout.write(self.style.SUCCESS(
            f"scanned={result['scanned']} healed={result['healed']} "
            f"created_visits={result['created_visits']}{suffix}"
        ))
