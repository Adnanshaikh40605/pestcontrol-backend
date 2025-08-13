from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from core.models import Client, Inquiry, JobCard, Renewal


class Command(BaseCommand):
    help = 'Populate the database with sample data for testing APIs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clients',
            type=int,
            default=20,
            help='Number of clients to create (default: 20)'
        )
        parser.add_argument(
            '--inquiries',
            type=int,
            default=30,
            help='Number of inquiries to create (default: 30)'
        )
        parser.add_argument(
            '--jobcards',
            type=int,
            default=50,
            help='Number of job cards to create (default: 50)'
        )
        parser.add_argument(
            '--renewals',
            type=int,
            default=25,
            help='Number of renewals to create (default: 25)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Renewal.objects.all().delete()
            JobCard.objects.all().delete()
            Inquiry.objects.all().delete()
            Client.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared'))

        self.stdout.write('Starting to populate sample data...')

        # Create sample clients
        clients = self.create_clients(options['clients'])
        
        # Create sample inquiries
        inquiries = self.create_inquiries(options['inquiries'])
        
        # Create sample job cards
        job_cards = self.create_job_cards(options['jobcards'], clients)
        
        # Create sample renewals
        self.create_renewals(options['renewals'], job_cards)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created:\n'
                f'- {len(clients)} clients\n'
                f'- {len(inquiries)} inquiries\n'
                f'- {len(job_cards)} job cards\n'
                f'- {options["renewals"]} renewals'
            )
        )

    def create_clients(self, count):
        """Create sample clients with realistic data."""
        cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 
            'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Surat',
            'Lucknow', 'Kanpur', 'Nagpur', 'Indore', 'Thane'
        ]
        
        first_names = [
            'Raj', 'Priya', 'Amit', 'Neha', 'Suresh', 'Anjali', 'Vikram', 'Meera',
            'Kumar', 'Sunita', 'Rahul', 'Pooja', 'Deepak', 'Ritu', 'Sanjay',
            'Kavita', 'Mohan', 'Reena', 'Arun', 'Sonia', 'Vishal', 'Anita'
        ]
        
        last_names = [
            'Sharma', 'Verma', 'Patel', 'Singh', 'Kumar', 'Gupta', 'Malhotra',
            'Kapoor', 'Joshi', 'Chopra', 'Reddy', 'Nair', 'Iyer', 'Menon',
            'Pillai', 'Nayar', 'Menon', 'Kurup', 'Nambiar', 'Warrier'
        ]

        clients = []
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            full_name = f"{first_name} {last_name}"
            
            # Generate unique mobile number
            mobile = f"9{random.randint(100000000, 999999999)}"
            while Client.objects.filter(mobile=mobile).exists():
                mobile = f"9{random.randint(100000000, 999999999)}"
            
            client = Client.objects.create(
                full_name=full_name,
                mobile=mobile,
                email=f"{first_name.lower()}.{last_name.lower()}@example.com" if random.random() > 0.3 else None,
                city=random.choice(cities),
                address=f"House No. {random.randint(1, 999)}, {random.choice(['Street', 'Lane', 'Road'])}, {random.choice(['Residential Area', 'Commercial Area', 'Industrial Area'])}",
                notes=random.choice([
                    "Regular customer, prefers morning appointments",
                    "Has pets, need to be careful with chemicals",
                    "Allergic to certain pesticides",
                    "Prefers eco-friendly solutions",
                    "Commercial property owner",
                    "Residential property",
                    "VIP customer",
                    "Referred by existing customer",
                    None, None, None  # 30% chance of no notes
                ]),
                is_active=random.choice([True, True, True, False])  # 75% active
            )
            clients.append(client)
            
        self.stdout.write(f'Created {count} clients')
        return clients

    def create_inquiries(self, count):
        """Create sample inquiries with realistic data."""
        service_types = [
            'Cockroach Control', 'Termite Treatment', 'Rodent Control', 
            'Bed Bug Treatment', 'Mosquito Control', 'Ant Control',
            'Spider Control', 'General Pest Control', 'Fumigation',
            'Pre-construction Termite Treatment', 'Post-construction Treatment'
        ]
        
        cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 
            'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Surat'
        ]
        
        statuses = ['New', 'Contacted', 'Converted', 'Closed']
        status_weights = [0.4, 0.3, 0.2, 0.1]  # 40% new, 30% contacted, etc.
        
        first_names = [
            'Ravi', 'Priyanka', 'Arjun', 'Divya', 'Karan', 'Zara', 'Ishaan', 'Aisha',
            'Vivaan', 'Myra', 'Aditya', 'Kiara', 'Shaurya', 'Anaya', 'Dhruv'
        ]
        
        last_names = [
            'Tiwari', 'Chauhan', 'Yadav', 'Kaur', 'Jain', 'Bhatt', 'Mishra',
            'Tiwari', 'Chauhan', 'Yadav', 'Kaur', 'Jain', 'Bhatt', 'Mishra'
        ]

        inquiries = []
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            name = f"{first_name} {last_name}"
            
            # Generate unique mobile number
            mobile = f"8{random.randint(100000000, 999999999)}"
            while Inquiry.objects.filter(mobile=mobile).exists():
                mobile = f"8{random.randint(100000000, 999999999)}"
            
            status = random.choices(statuses, weights=status_weights)[0]
            
            inquiry = Inquiry.objects.create(
                name=name,
                mobile=mobile,
                email=f"{first_name.lower()}.{last_name.lower()}@example.com" if random.random() > 0.2 else None,
                message=random.choice([
                    "Need urgent pest control service for my home",
                    "Looking for termite treatment for my office",
                    "Cockroach problem in kitchen, need immediate help",
                    "Bed bugs in bedroom, very disturbing",
                    "Rodent infestation in basement",
                    "Mosquito problem in garden area",
                    "Ants everywhere, need professional help",
                    "Spider webs all over the house",
                    "General pest control required for new property",
                    "Fumigation needed for warehouse",
                    "Pre-construction termite treatment required"
                ]),
                service_interest=random.choice(service_types),
                city=random.choice(cities),
                status=status
            )
            inquiries.append(inquiry)
            
        self.stdout.write(f'Created {count} inquiries')
        return inquiries

    def create_job_cards(self, count, clients):
        """Create sample job cards with realistic data."""
        service_types = [
            'Cockroach Control', 'Termite Treatment', 'Rodent Control', 
            'Bed Bug Treatment', 'Mosquito Control', 'Ant Control',
            'Spider Control', 'General Pest Control', 'Fumigation',
            'Pre-construction Termite Treatment', 'Post-construction Treatment'
        ]
        
        statuses = ['Enquiry', 'WIP', 'Done', 'Hold', 'Cancel', 'Inactive']
        status_weights = [0.2, 0.3, 0.3, 0.1, 0.05, 0.05]
        
        payment_statuses = ['Unpaid', 'Paid']
        payment_weights = [0.4, 0.6]  # 40% unpaid, 60% paid
        
        technician_names = [
            'Rajesh Kumar', 'Amit Singh', 'Vikram Patel', 'Suresh Sharma',
            'Deepak Verma', 'Rahul Gupta', 'Mohan Joshi', 'Arun Malhotra',
            'Sanjay Kapoor', 'Vishal Chopra', 'Kumar Reddy', 'Nair Menon'
        ]
        
        # Generate dates for the past 6 months and next 3 months
        today = date.today()
        past_dates = [today - timedelta(days=i) for i in range(1, 180)]
        future_dates = [today + timedelta(days=i) for i in range(1, 90)]
        all_dates = past_dates + future_dates

        job_cards = []
        for i in range(count):
            client = random.choice(clients)
            status = random.choices(statuses, weights=status_weights)[0]
            payment_status = random.choices(payment_statuses, weights=payment_weights)[0]
            
            # Set schedule date based on status
            if status == 'Done':
                schedule_date = random.choice(past_dates)
            elif status == 'Enquiry':
                schedule_date = random.choice(future_dates)
            else:
                schedule_date = random.choice(all_dates)
            
            # Set next service date for completed jobs
            next_service_date = None
            if status == 'Done' and random.random() > 0.5:
                next_service_date = schedule_date + timedelta(days=random.randint(30, 365))
            
            # Generate realistic pricing
            base_price = random.randint(800, 3000)
            price_subtotal = Decimal(str(base_price))
            tax_percent = random.choice([5, 12, 18, 28])
            
            job_card = JobCard.objects.create(
                client=client,
                status=status,
                service_type=random.choice(service_types),
                schedule_date=schedule_date,
                technician_name=random.choice(technician_names),
                price_subtotal=price_subtotal,
                tax_percent=tax_percent,
                payment_status=payment_status,
                next_service_date=next_service_date,
                notes=random.choice([
                    "Customer requested eco-friendly products",
                    "Need to avoid kitchen area during treatment",
                    "Customer has small children, extra care required",
                    "Commercial property, need to work after hours",
                    "Customer prefers weekend appointments",
                    "Urgent service required",
                    "Follow-up visit needed",
                    "Customer satisfied with service",
                    "Need to reschedule due to customer request",
                    "Additional treatment required",
                    None, None, None  # 30% chance of no notes
                ])
            )
            job_cards.append(job_card)
            
        self.stdout.write(f'Created {count} job cards')
        return job_cards

    def create_renewals(self, count, job_cards):
        """Create sample renewals with realistic data."""
        # Filter only completed job cards for renewals
        completed_jobs = [jc for jc in job_cards if jc.status == 'Done']
        
        if not completed_jobs:
            self.stdout.write('No completed job cards found for renewals')
            return
        
        renewals = []
        for i in range(count):
            job_card = random.choice(completed_jobs)
            
            # Generate due date (past, present, or future)
            today = date.today()
            if random.random() > 0.7:  # 30% chance of overdue
                due_date = today - timedelta(days=random.randint(1, 60))
                status = 'Due'
            elif random.random() > 0.5:  # 20% chance of due soon
                due_date = today + timedelta(days=random.randint(1, 30))
                status = 'Due'
            else:  # 50% chance of future due date
                due_date = today + timedelta(days=random.randint(31, 365))
                status = random.choice(['Due', 'Completed'])
            
            renewal = Renewal.objects.create(
                jobcard=job_card,
                due_date=due_date,
                status=status,
                remarks=random.choice([
                    "Annual renewal due",
                    "Customer requested early renewal",
                    "Follow-up treatment required",
                    "Preventive maintenance",
                    "Customer satisfied, continuing service",
                    "Special package renewal",
                    "Corporate client renewal",
                    "VIP customer priority renewal",
                    "Seasonal treatment renewal",
                    "Emergency renewal due to infestation",
                    None, None, None  # 30% chance of no remarks
                ])
            )
            renewals.append(renewal)
            
        self.stdout.write(f'Created {count} renewals') 