from django.core.management.base import BaseCommand

from core.pricing.seed import seed_pricing_master


class Command(BaseCommand):
    help = 'Import legacy Mumbai/Lonavala rates into Pricing Master (insert only, never overwrites)'

    def handle(self, *args, **options):
        result = seed_pricing_master()
        for region, stats in result.items():
            self.stdout.write(
                self.style.SUCCESS(
                    f'{region}: created={stats["created"]}, skipped={stats["skipped"]} (existing unchanged)',
                ),
            )
