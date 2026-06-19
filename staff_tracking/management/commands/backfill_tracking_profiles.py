from django.core.management.base import BaseCommand

from staff_tracking.services import backfill_profiles_for_technicians


class Command(BaseCommand):
    help = 'Create tracking profiles for all active technicians.'

    def handle(self, *args, **options):
        count = backfill_profiles_for_technicians()
        self.stdout.write(self.style.SUCCESS(f'Created/verified {count} tracking profiles.'))
