"""Phase 5 customer app API tests."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, Feedback, JobCard, Location, PricingRate, PricingRegion, State
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
        self.country, _ = Country.objects.get_or_create(
            name='India Customer Test',
            defaults={'is_active': True},
        )
        self.state, _ = State.objects.get_or_create(
            country=self.country,
            name='Maharashtra Customer Test',
            defaults={'is_active': True},
        )
        self.city, _ = City.objects.get_or_create(
            state=self.state,
            name='Mumbai',
            defaults={'is_active': True},
        )
        self.location, _ = Location.objects.get_or_create(
            city=self.city,
            name='Andheri West',
            defaults={'is_active': True},
        )

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

    @override_settings(DEBUG=True, CUSTOMER_OTP_FIXED='1234')
    def test_otp_register_and_login(self):
        send = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000111222', 'purpose': 'register', 'full_name': 'Otp User'},
            format='json',
        )
        self.assertEqual(send.status_code, 200, send.data)
        self.assertEqual(send.data.get('dev_otp'), '1234')

        verify = self.api.post(
            '/api/customer/otp/verify/',
            {'mobile': '9000111222', 'otp': '1234', 'purpose': 'register', 'full_name': 'Otp User'},
            format='json',
        )
        self.assertEqual(verify.status_code, 200, verify.data)
        self.assertIn('access', verify.data)
        self.assertEqual(verify.data['customer']['full_name'], 'Otp User')

        self.api.credentials()
        send_login = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000111222', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(send_login.status_code, 200, send_login.data)
        login = self.api.post(
            '/api/customer/otp/verify/',
            {'mobile': '9000111222', 'otp': '1234', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.assertIn('access', login.data)

    @override_settings(DEBUG=True, CUSTOMER_OTP_FIXED='1234')
    def test_login_otp_unregistered_mobile_can_verify_then_register(self):
        """Login OTP is allowed without an account; verify returns not_registered."""
        send = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000999888', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(send.status_code, 200, send.data)

        verify = self.api.post(
            '/api/customer/otp/verify/',
            {'mobile': '9000999888', 'otp': '1234', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(verify.status_code, 404, verify.data)
        self.assertEqual(verify.data.get('code'), 'not_registered')
        self.assertEqual(verify.data.get('action'), 'register')
        self.assertEqual(verify.data.get('mobile'), '9000999888')
        self.assertIn('No account found', verify.data.get('error', ''))
        self.assertIn('register', verify.data.get('error', '').lower())

    def test_catalog_lists_rates_with_package_tiers(self):
        res = self.api.get('/api/customer/catalog/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(len(res.data['results']) >= 1)
        row = res.data['results'][0]
        self.assertIn('standard', row['package_tiers'])
        self.assertIn('premium', row['package_tiers'])
        self.assertEqual(Decimal(row['package_tiers']['standard']), Decimal('1000.00'))
        self.assertEqual(Decimal(row['package_tiers']['premium']), Decimal('1150.00'))

    @override_settings(CUSTOMER_ONLINE_PAYMENT_ENABLED=True)
    def test_book_track_pay_rate_flow(self):
        self._register()
        with self.captureOnCommitCallbacks(execute=True):
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
        self.assertIsNotNone(job.sent_to_app_at)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.PENDING)
        # Customer bookings must land in the Partner App open pool.
        job.refresh_from_db()
        self.assertIsNotNone(job.sent_to_app_at)

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

    def test_pay_disabled_by_default(self):
        self._register(mobile='9444555666')
        book = self.api.post(
            '/api/customer/bookings/',
            {
                'pricing_rate_id': self.rate.id,
                'package_tier': 'standard',
                'address': 'No Pay Lane',
            },
            format='json',
        )
        self.assertEqual(book.status_code, 201, book.data)
        booking_id = book.data['booking']['id']
        pay = self.api.post(
            f'/api/customer/bookings/{booking_id}/pay/',
            {'payment_reference': 'SHOULD-FAIL'},
            format='json',
        )
        self.assertEqual(pay.status_code, 400)
        self.assertEqual(pay.data.get('code'), 'payment_disabled')

    @override_settings(CUSTOMER_ONLINE_PAYMENT_ENABLED=True)
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

    def test_cities_and_locations_public(self):
        cities = self.api.get('/api/customer/cities/')
        self.assertEqual(cities.status_code, 200, cities.data)
        names = [row['name'] for row in cities.data['results']]
        self.assertIn('Mumbai', names)

        missing = self.api.get('/api/customer/locations/')
        self.assertEqual(missing.status_code, 400)

        locations = self.api.get(f'/api/customer/locations/?city_id={self.city.id}')
        self.assertEqual(locations.status_code, 200, locations.data)
        area_names = [row['name'] for row in locations.data['results']]
        self.assertIn('Andheri West', area_names)

    def test_booking_with_master_city_location_and_coordinates(self):
        self._register()
        with self.captureOnCommitCallbacks(execute=True):
            book = self.api.post(
                '/api/customer/bookings/',
                {
                    'service_type': 'General Pest Control',
                    'pricing_rate_id': self.rate.id,
                    'package_tier': 'standard',
                    'address': 'Flat 12, Sunshine Apartments',
                    'full_address': 'Flat 12, Sunshine Apartments, Andheri West, Mumbai, Maharashtra 400053, India',
                    'city': 'Mumbai',
                    'area': 'Andheri West',
                    'master_city_id': self.city.id,
                    'master_location_id': self.location.id,
                    'latitude': '19.113600',
                    'longitude': '72.869700',
                    'bhk_size': '1 BHK',
                },
                format='json',
            )
        self.assertEqual(book.status_code, 201, book.data)
        job = JobCard.objects.get(id=book.data['booking']['id'])
        self.assertEqual(job.master_city_id, self.city.id)
        self.assertEqual(job.master_location_id, self.location.id)
        self.assertEqual(job.full_address, 'Flat 12, Sunshine Apartments, Andheri West, Mumbai, Maharashtra 400053, India')
        self.assertEqual(str(job.service_latitude), '19.113600')
        self.assertEqual(str(job.service_longitude), '72.869700')
        self.assertEqual(job.client_address, 'Flat 12, Sunshine Apartments')

    def test_booking_rejects_location_city_mismatch(self):
        self._register(mobile='9000111333')
        pune, _ = City.objects.get_or_create(
            state=self.state,
            name='Pune',
            defaults={'is_active': True},
        )
        res = self.api.post(
            '/api/customer/bookings/',
            {
                'pricing_rate_id': self.rate.id,
                'package_tier': 'standard',
                'address': 'Some Street',
                'master_city_id': pune.id,
                'master_location_id': self.location.id,
            },
            format='json',
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.assertIn('master_location_id', str(res.data))

    @override_settings(GOOGLE_MAPS_API_KEY='test-google-key')
    def test_places_autocomplete_proxy(self):
        from unittest.mock import patch

        mock_payload = {
            'status': 'OK',
            'predictions': [
                {
                    'place_id': 'abc123',
                    'description': 'Kurla, Mumbai, Maharashtra, India',
                    'structured_formatting': {'main_text': 'Kurla'},
                }
            ],
        }
        with patch('customer.places.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_payload
            res = self.api.get('/api/customer/places/autocomplete/?input=kurla')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['results'][0]['main_text'], 'Kurla')
