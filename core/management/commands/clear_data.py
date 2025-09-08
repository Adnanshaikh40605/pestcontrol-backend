#!/usr/bin/env python
"""
Django management command to clear all dummy data from local database.
This will remove all JobCards and Inquiries from the local database only.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import JobCard, Inquiry, Renewal


class Command(BaseCommand):
    help = 'Clear all dummy data (JobCards, Inquiries, and Renewals) from local database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all data',
        )
    
    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will delete ALL JobCards, Inquiries, and Renewals from the database.\n'
                    'Run with --confirm to proceed.'
                )
            )
            return
        
        try:
            with transaction.atomic():
                # Count existing records
                jobcard_count = JobCard.objects.count()
                inquiry_count = Inquiry.objects.count()
                renewal_count = Renewal.objects.count()
                
                self.stdout.write(
                    f'Found {jobcard_count} JobCards, {inquiry_count} Inquiries, '
                    f'and {renewal_count} Renewals to delete.'
                )
                
                # Delete all records
                # Delete renewals first (they reference jobcards)
                deleted_renewals = Renewal.objects.all().delete()[0]
                
                # Delete jobcards (they reference inquiries)
                deleted_jobcards = JobCard.objects.all().delete()[0]
                
                # Delete inquiries
                deleted_inquiries = Inquiry.objects.all().delete()[0]
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted:\n'
                        f'  - {deleted_renewals} Renewals\n'
                        f'  - {deleted_jobcards} JobCards\n'
                        f'  - {deleted_inquiries} Inquiries\n'
                        f'Database cleared successfully!'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing data: {str(e)}')
            )
            raise