"""
Django management command to populate the database with dummy data for testing.
Usage: python manage.py populate_dummy_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import random
from datetime import timedelta

from core.models import Client, Inquiry, JobCard, Renewal


class Command(BaseCommand):
    help = 'Populate database with dummy data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of dummy records to create (default: 20)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear_existing = options['clear']

        if clear_existing:
            self.stdout.write('Clearing existing data...')
            Renewal.objects.all().delete()
            JobCard.objects.all().delete()
            Inquiry.objects.all().delete()
            Client.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared'))

        self.stdout.write(f'Creating {count} dummy records...')

        try:
            with transaction.atomic():
                # Create dummy clients first
                clients = self._create_dummy_clients(count)
                
                # Create dummy inquiries
                inquiries = self._create_dummy_inquiries(count)
                
                # Create dummy job cards
                job_cards = self._create_dummy_job_cards(count, clients)
                
                # Create dummy renewals
                renewals = self._create_dummy_renewals(count, job_cards)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {count} dummy records:\n'
                    f'- {len(clients)} Clients\n'
                    f'- {len(inquiries)} Inquiries\n'
                    f'- {len(job_cards)} Job Cards\n'
                    f'- {len(renewals)} Renewals'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating dummy data: {str(e)}')
            )

    def _create_dummy_clients(self, count):
        """Create dummy clients."""
        cities = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad']
        clients = []

        for i in range(count):
            # Generate unique mobile number starting from a different range
            mobile = f'98765{30000+i:05d}'
            
            client = Client.objects.create(
                full_name=f'Client {i+1:02d}',
                mobile=mobile,
                email=f'client{i+1:02d}@example.com',
                city=random.choice(cities),
                address=f'Address {i+1}, Street {i+1}, {random.choice(cities)}',
                notes=f'Sample client {i+1} for testing purposes',
                is_active=random.choice([True, True, True, False])  # 75% active
            )
            clients.append(client)

        return clients

    def _create_dummy_inquiries(self, count):
        """Create dummy inquiries."""
        service_interests = [
            'Pest Control', 'Termite Treatment', 'Rodent Control', 'Cockroach Control',
            'Bed Bug Treatment', 'Mosquito Control', 'General Pest Management'
        ]
        statuses = ['New', 'Contacted', 'Converted', 'Closed']
        cities = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad']
        inquiries = []

        for i in range(count):
            # Generate unique mobile number starting from a different range
            mobile = f'98765{40000+i:05d}'
            
            inquiry = Inquiry.objects.create(
                name=f'Inquiry {i+1:02d}',
                mobile=mobile,
                email=f'inquiry{i+1:02d}@example.com',
                message=f'This is a sample inquiry {i+1} for testing purposes. Looking for pest control services.',
                service_interest=random.choice(service_interests),
                city=random.choice(cities),
                status=random.choice(statuses),
                is_read=random.choice([True, False])
            )
            inquiries.append(inquiry)

        return inquiries

    def _create_dummy_job_cards(self, count, clients):
        """Create dummy job cards."""
        service_types = [
            'Pest Control', 'Termite Treatment', 'Rodent Control', 'Cockroach Control',
            'Bed Bug Treatment', 'Mosquito Control', 'General Pest Management'
        ]
        statuses = ['Enquiry', 'WIP', 'Done', 'Hold', 'Cancel', 'Inactive']
        payment_statuses = ['Unpaid', 'Paid']
        technician_names = [
            'Rajesh Kumar', 'Amit Singh', 'Suresh Patel', 'Mohan Sharma',
            'Vikram Verma', 'Anil Gupta', 'Prakash Joshi', 'Ramesh Tiwari'
        ]
        job_cards = []

        for i in range(count):
            # Random date within last 30 days
            random_days = random.randint(-30, 0)
            schedule_date = timezone.now().date() + timedelta(days=random_days)
            
            # Random price between 500 and 5000
            price_subtotal = Decimal(random.randint(500, 5000))
            
            job_card = JobCard.objects.create(
                client=random.choice(clients),
                status=random.choice(statuses),
                service_type=random.choice(service_types),
                schedule_date=schedule_date,
                technician_name=random.choice(technician_names),
                price_subtotal=price_subtotal,
                tax_percent=random.choice([18, 12, 5, 0]),
                payment_status=random.choice(payment_statuses),
                next_service_date=schedule_date + timedelta(days=random.randint(30, 180)),
                notes=f'Sample job card {i+1} for testing purposes'
            )
            job_cards.append(job_card)

        return job_cards

    def _create_dummy_renewals(self, count, job_cards):
        """Create dummy renewals."""
        statuses = ['Due', 'Completed']
        renewals = []

        for i in range(count):
            # Random due date within next 90 days
            random_days = random.randint(1, 90)
            due_date = timezone.now() + timedelta(days=random_days)
            
            renewal = Renewal.objects.create(
                jobcard=random.choice(job_cards),
                due_date=due_date,
                status=random.choice(statuses),
                remarks=f'Sample renewal {i+1} for testing purposes'
            )
            renewals.append(renewal)

        return renewals
