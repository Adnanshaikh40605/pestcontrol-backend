from django.core.management.base import BaseCommand

from core.reminder_sync import backfill_legacy_reminders


class Command(BaseCommand):
    help = 'Copy pending legacy inquiry reminders into the unified Reminder table.'

    def handle(self, *args, **options):
        created = backfill_legacy_reminders()
        self.stdout.write(self.style.SUCCESS(f'Created {created} reminder record(s).'))
