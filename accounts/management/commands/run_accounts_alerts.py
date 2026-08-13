from django.core.management.base import BaseCommand

from accounts.services.alerts import run_accounts_alerts
from accounts.services.rollups import rebuild_daily_pnl, rebuild_monthly_pnl


class Command(BaseCommand):
    help = 'Rebuild today P&L rollups and generate accounts alerts'

    def handle(self, *args, **options):
        rebuild_daily_pnl()
        rebuild_monthly_pnl()
        stats = run_accounts_alerts()
        self.stdout.write(self.style.SUCCESS(str(stats)))
