from django.core.management.base import BaseCommand

from accounts.services.overhead import allocate_monthly_overhead


class Command(BaseCommand):
    help = 'Allocate monthly office/marketing overhead per completed booking'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=None)
        parser.add_argument('--month', type=int, default=None)

    def handle(self, *args, **options):
        rows = allocate_monthly_overhead(year=options['year'], month=options['month'])
        for row in rows:
            self.stdout.write(
                f'{row.branch.name} {row.year}-{row.month:02d}: '
                f'overhead ₹{row.total_overhead} / {row.completed_bookings} = ₹{row.overhead_per_booking}'
            )
