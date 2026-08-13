from django.core.management.base import BaseCommand

from accounts.services.rollups import rebuild_monthly_pnl, rebuild_range


class Command(BaseCommand):
    help = 'Rebuild daily/monthly accounts P&L rollups'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=31)

    def handle(self, *args, **options):
        rebuild_range(days=options['days'])
        rebuild_monthly_pnl()
        self.stdout.write(self.style.SUCCESS(f'Rebuilt last {options["days"]} days + current month'))
