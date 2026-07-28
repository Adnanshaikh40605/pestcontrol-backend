from django.core.management.base import BaseCommand

from core.booking_report_dedupe import dedupe_booking_report_clients


class Command(BaseCommand):
    help = 'Merge duplicate BookingReportClient rows that share the same mobile number'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be deleted without changing data',
        )

    def handle(self, *args, **options):
        result = dedupe_booking_report_clients(dry_run=bool(options['dry_run']))
        style = self.style.WARNING if result['dry_run'] else self.style.SUCCESS
        self.stdout.write(style(str(result)))
        if result['remaining_duplicate_groups']:
            self.stdout.write(
                self.style.ERROR(
                    f"Still have {result['remaining_duplicate_groups']} duplicate mobile groups"
                )
            )
