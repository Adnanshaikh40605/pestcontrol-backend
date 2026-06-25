from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import City, Client, Country, CRMInquiry, JobCard, Location, State
from core.services import CRMInquiryService, JobCardService


class JobCardCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='creator', password='pass1234')
        self.client_record = Client.objects.create(full_name='Naziya', mobile='9876543210')
        self.schedule = datetime(2026, 6, 15, 10, 0, tzinfo=dt_timezone.utc)
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Test')
        city, _ = City.objects.get_or_create(state=state, name='Mumbai Test')
        norm = Location.normalize_text('API Test Area')
        self.location, _ = Location.objects.get_or_create(
            city=city,
            normalized_name=norm,
            defaults={'name': 'API Test Area'},
        )

    def test_create_amc_booking_sets_next_service_without_pk_error(self):
        job = JobCardService.create_jobcard(
            {
                'client_data': {
                    'full_name': 'Naziya',
                    'mobile': '9876543210',
                },
                'service_type': 'Cockroach / Ants',
                'service_category': JobCard.ServiceCategory.AMC,
                'schedule_datetime': self.schedule,
                'price': '2500',
                'reference': 'Poster',
                'status': JobCard.JobStatus.PENDING,
            },
            user=self.user,
        )
        self.assertIsNotNone(job.pk)
        self.assertEqual(job.max_cycle, 3)
        self.assertIsNotNone(job.next_service_date)
        self.assertEqual(job.total_amount, Decimal('2500.00'))

    def test_create_via_api_returns_201(self):
        response = self.api.post(
            '/api/v1/jobcards/',
            {
                'client_data': {
                    'full_name': 'API Client',
                    'mobile': '9123456789',
                },
                'service_type': 'Bed Bugs',
                'service_category': 'One-Time Service',
                'schedule_datetime': self.schedule.isoformat(),
                'price': '3000',
                'reference': 'Poster',
                'status': 'Pending',
                'master_location': self.location.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['max_cycle'], 2)

    def test_complete_booking_records_price_from_job_card(self):
        job = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.schedule,
            price='2500',
            total_amount=Decimal('2500.00'),
            reference='Other',
            status=JobCard.JobStatus.PENDING,
        )
        response = self.api.patch(
            f'/api/v1/jobcards/{job.id}/',
            {
                'status': 'Done',
                'payment_mode': 'Online',
                'payment_collection_type': 'full',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        job.refresh_from_db()
        self.assertEqual(job.paid_amount, Decimal('2500.00'))
        self.assertEqual(job.pending_amount, Decimal('0.00'))
        self.assertEqual(job.payment_status, JobCard.PaymentStatus.PAID)

    def test_update_manual_price_syncs_service_items(self):
        job = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.schedule,
            price='1200',
            total_amount=Decimal('1200.00'),
            pending_amount=Decimal('1200.00'),
            reference='Instagram',
            status=JobCard.JobStatus.ON_PROCESS,
            service_items=[
                {
                    'service': 'Cockroach / Ants',
                    'plan': 'One Time Service',
                    'area': '2 BHK',
                    'amount': 1200,
                },
            ],
        )
        response = self.api.patch(
            f'/api/v1/jobcards/{job.id}/',
            {
                'price': '1000',
                'service_items': [
                    {
                        'service': 'Cockroach / Ants',
                        'plan': 'One Time Service',
                        'area': '2 BHK',
                        'amount': 1200,
                    },
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        job.refresh_from_db()
        self.assertEqual(job.price, '1000')
        self.assertEqual(job.service_items[0]['amount'], 1000.0)
        self.assertEqual(job.total_amount, Decimal('1000.00'))
        self.assertEqual(job.pending_amount, Decimal('1000.00'))


class CRMInquiryConversionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='crm', password='pass1234')

    def test_convert_inquiry_creates_booking_with_price(self):
        inquiry = CRMInquiry.objects.create(
            name='Naziya Sayyed',
            mobile='9867123456',
            location='Pathan Wadi Malad, Malad East, Mumbai',
            pest_type='Cockroach / Ants',
            service_frequency='amc',
            remark='2 BHK AMC',
            created_by=self.user,
        )
        job = CRMInquiryService.convert_to_booking(inquiry.id, user=self.user)
        self.assertIsNotNone(job.pk)
        self.assertTrue(job.price)
        self.assertGreater(job.total_amount, 0)
