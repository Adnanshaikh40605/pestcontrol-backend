"""Phase 5 customer app API tests."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Client, Feedback, JobCard, PricingRate, PricingRegion
from customer.models import CustomerAccount
from customer.utils import generate_customer_tokens


@override_settings(REVENUE_MODEL_V2=True)
class CustomerApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.region, _ = PricingRegion.objects.get_or_create(
            slug='customer-test-region',
            defaults={
                'name': 'Customer Test Region',
                'is_default': True,
                'is_active': True,
            },
        )
        self.region.is_default = True
        self.region.is_active = True
        self.region.save(update_fields=['is_default', 'is_active', 'updated_at'])
        self.rate, _ = PricingRate.objects.get_or_create(
            region=self.region,
            service_package='General Pest Control',
            plan_type='One Time Service',
            area_key='1 BHK',
            defaults={
                'amount': Decimal('1000.00'),
                'is_active': True,
            },
        )
        self.rate.amount = Decimal('1000.00')
        self.rate.is_active = True
        self.rate.save(update_fields=['amount', 'is_active', 'updated_at'])

    def _register(self, mobile='9888777666', name='Cust User'):
        res = self.api.post(
            '/api/customer/register/',
            {
                'full_name': name,
                'mobile': mobile,
                'password': 'secret12',
                'email': 'cust@example.com',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def test_register_login_profile(self):
        data = self._register()
        self.assertIn('access', data)
        self.assertEqual(data['customer']['mobile'], '9888777666')

        self.api.credentials()
        login = self.api.post(
            '/api/customer/login/',
            {'mobile': '9888777666', 'password': 'secret12'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        profile = self.api.get('/api/customer/profile/')
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data['customer']['full_name'], 'Cust User')

    def test_catalog_lists_rates_with_package_tiers(self):
        res = self.api.get('/api/customer/catalog/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(len(res.data['results']) >= 1)
        row = res.data['results'][0]
        self.assertIn('standard', row['package_tiers'])
        self.assertIn('premium', row['package_tiers'])
        self.assertEqual(Decimal(row['package_tiers']['standard']), Decimal('1000.00'))
        self.assertEqual(Decimal(row['package_tiers']['premium']), Decimal('1150.00'))

    def test_book_track_pay_rate_flow(self):
        self._register()
        book = self.api.post(
            '/api/customer/bookings/',
            {
                'service_type': 'General Pest Control',
                'pricing_rate_id': self.rate.id,
                'package_tier': 'standard',
                'address': '12 Test Lane',
                'city': 'Mumbai',
                'bhk_size': '1 BHK',
            },
            format='json',
        )
        self.assertEqual(book.status_code, 201, book.data)
        booking_id = book.data['booking']['id']

        job = JobCard.objects.get(id=booking_id)
        self.assertEqual(job.creation_source, 'customer_app')
        self.assertEqual(job.reference, 'Customer App')
        self.assertEqual(Decimal(str(job.total_amount or job.price)), Decimal('1000.00'))

        detail = self.api.get(f'/api/customer/bookings/{booking_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['id'], booking_id)

        pay = self.api.post(
            f'/api/customer/bookings/{booking_id}/pay/',
            {'payment_reference': 'TEST-PAY-1'},
            format='json',
        )
        self.assertEqual(pay.status_code, 200, pay.data)
        job.refresh_from_db()
        self.assertEqual(job.payment_mode, JobCard.PaymentMode.ONLINE)

        # Complete job then rate
        job.status = JobCard.JobStatus.DONE
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'completed_at', 'updated_at'])

        rate = self.api.post(
            f'/api/customer/bookings/{booking_id}/rate/',
            {'rating': 5, 'remark': 'Great', 'technician_behavior': 'excellent'},
            format='json',
        )
        self.assertEqual(rate.status_code, 200, rate.data)
        self.assertTrue(Feedback.objects.filter(booking=job, rating=5).exists())

        history = self.api.get('/api/customer/history/')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.data['results']), 1)

        invoice = self.api.get(f'/api/customer/bookings/{booking_id}/invoice/')
        self.assertEqual(invoice.status_code, 200)
        self.assertEqual(invoice.data['code'], job.code)

    def test_cannot_rate_others_booking(self):
        self._register(mobile='9111222333')
        other_client = Client.objects.create(full_name='Other', mobile='9000111222')
        job = JobCard.objects.create(
            client=other_client,
            service_type='General Pest',
            price='500',
            status=JobCard.JobStatus.DONE,
            completed_at=timezone.now(),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        res = self.api.post(
            f'/api/customer/bookings/{job.id}/rate/',
            {'rating': 4},
            format='json',
        )
        self.assertEqual(res.status_code, 404)

    def test_premium_applies_markup(self):
        self._register(mobile='9222333444')
        book = self.api.post(
            '/api/customer/bookings/',
            {
                'service_type': 'General Pest Control',
                'pricing_rate_id': self.rate.id,
                'package_tier': 'premium',
                'address': '99 Premium Rd',
            },
            format='json',
        )
        self.assertEqual(book.status_code, 201, book.data)
        job = JobCard.objects.get(id=book.data['booking']['id'])
        self.assertEqual(job.package_tier, 'premium')
        self.assertEqual(Decimal(str(job.total_amount or job.price)), Decimal('1150.00'))

    def test_pay_is_idempotent(self):
        self._register(mobile='9333444555')
        book = self.api.post(
            '/api/customer/bookings/',
            {
                'pricing_rate_id': self.rate.id,
                'package_tier': 'standard',
                'address': '1 Idempotent Rd',
            },
            format='json',
        )
        self.assertEqual(book.status_code, 201, book.data)
        booking_id = book.data['booking']['id']
        first = self.api.post(
            f'/api/customer/bookings/{booking_id}/pay/',
            {'payment_reference': 'PAY-1'},
            format='json',
        )
        self.assertEqual(first.status_code, 200, first.data)
        second = self.api.post(
            f'/api/customer/bookings/{booking_id}/pay/',
            {'payment_reference': 'PAY-2'},
            format='json',
        )
        self.assertEqual(second.status_code, 200, second.data)
        from core.models import BookingPayment
        self.assertEqual(BookingPayment.objects.filter(jobcard_id=booking_id).count(), 1)

    def test_contractual_booking_maps_to_society(self):
        self._register(mobile='9222333444')
        book = self.api.post(
            '/api/customer/bookings/',
            {
                'pricing_rate_id': self.rate.id,
                'package_tier': 'standard',
                'booking_type': 'contractual',
                'address': 'Society Gate A',
                'schedule_datetime': timezone.now().isoformat(),
            },
            format='json',
        )
        self.assertEqual(book.status_code, 201, book.data)
        job = JobCard.objects.get(id=book.data['booking']['id'])
        self.assertEqual(job.job_type, JobCard.JobType.SOCIETY)
        self.assertEqual(job.commercial_type, JobCard.CommercialType.SOCIETY)
        self.assertEqual(job.payment_model, JobCard.PaymentModel.REVENUE_SHARING)

    def test_amc_schedule_lists_parent(self):
        self._register(mobile='9111222333')
        book = self.api.post(
            '/api/customer/bookings/',
            {
                'pricing_rate_id': self.rate.id,
                'package_tier': 'standard',
                'booking_type': 'amc',
                'address': 'AMC Lane',
            },
            format='json',
        )
        self.assertEqual(book.status_code, 201, book.data)
        parent_id = book.data['booking']['id']
        parent = JobCard.objects.get(id=parent_id)
        parent.is_amc_main_booking = True
        parent.save(update_fields=['is_amc_main_booking', 'updated_at'])
        JobCard.objects.create(
            client=parent.client,
            parent_job=parent,
            service_type=parent.service_type,
            price=parent.price,
            total_amount=parent.total_amount,
            status=JobCard.JobStatus.PENDING,
            service_cycle=2,
            max_cycle=3,
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        res = self.api.get('/api/customer/amc-schedule/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['parent']['id'], parent_id)
        self.assertEqual(len(res.data['results'][0]['visits']), 1)
