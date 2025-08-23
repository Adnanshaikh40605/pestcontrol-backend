from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import Client
import re


class Command(BaseCommand):
    help = 'Check for duplicate mobile numbers in Client model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix duplicate mobile numbers by cleaning them',
        )

    def handle(self, *args, **options):
        self.stdout.write('Checking for duplicate mobile numbers...')
        
        # Get all clients
        clients = Client.objects.all()
        
        # Group by cleaned mobile numbers
        mobile_groups = {}
        for client in clients:
            cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(client.mobile))
            if cleaned_mobile not in mobile_groups:
                mobile_groups[cleaned_mobile] = []
            mobile_groups[cleaned_mobile].append(client)
        
        # Find duplicates
        duplicates = {mobile: clients for mobile, clients in mobile_groups.items() if len(clients) > 1}
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate mobile numbers found!'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {len(duplicates)} duplicate mobile numbers:'))
        
        for mobile, clients in duplicates.items():
            self.stdout.write(f'\nMobile: {mobile}')
            for client in clients:
                self.stdout.write(f'  - Client ID: {client.id}, Name: {client.full_name}, Mobile: "{client.mobile}"')
        
        if options['fix']:
            self.stdout.write('\nAttempting to fix duplicates...')
            fixed_count = 0
            
            for mobile, clients in duplicates.items():
                # Keep the first client, update others to have cleaned mobile
                primary_client = clients[0]
                for client in clients[1:]:
                    if client.mobile != mobile:
                        old_mobile = client.mobile
                        client.mobile = mobile
                        try:
                            client.save()
                            self.stdout.write(f'  Fixed: Client {client.id} mobile "{old_mobile}" -> "{mobile}"')
                            fixed_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  Failed to fix client {client.id}: {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} mobile numbers'))
        else:
            self.stdout.write('\nUse --fix to attempt to fix duplicate mobile numbers')
