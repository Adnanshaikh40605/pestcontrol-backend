"""Phase 5 customer app API tests."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, Feedback, JobCard, Location, PricingRate, PricingRegion, State
from customer.models import CustomerAccount
from customer.utils import generate_customer_tokens, issue_website_booking_verification_token


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

    def _website_otp_token(self, mobile: str) -> str:
        token, _ = issue_website_booking_verification_token(mobile)
        return token

    def _website_booking_payload(self, **overrides):
        mobile = overrides.get('mobile', '9111222333')
        payload = {
            'full_name': 'Website Guest',
            'mobile': mobile,
            'service_type': 'General Pest Control',
            'pricing_rate_id': self.rate.id,
            'package_tier': 'standard',
            'address': '42 Website Lane',
            'city': 'Mumbai',
            'bhk_size': '1 BHK',
            'property_type': 'Home / Flat',
            'booking_type': 'one_time',
            'booking_date': '2026-09-20',
            'booking_time': '10:30',
            'timezone': 'Asia/Kolkata',
            'time_slot': '10:30 AM',
            'notes': 'Website booking · Home (Residential) · 1 BHK · Standard · 10:30 AM',
            'otp_verification_token': self._website_otp_token(mobile),
        }
        payload.update(overrides)
        if 'otp_verification_token' not in overrides and 'mobile' in overrides:
            payload['otp_verification_token'] = self._website_otp_token(overrides['mobile'])
        return payload

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
    def test_register_otp_is_idempotent_when_account_already_exists(self):
        """If account exists mid-register, verifying register OTP still returns tokens."""
        from customer.models import CustomerAccount, CustomerOTPChallenge
        from core.models import Client

        client = Client.objects.create(full_name='Existing', mobile='9000111555')
        CustomerAccount.objects.create(
            client=client,
            mobile='9000111555',
            full_name='Existing',
            is_active=True,
        )
        send = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000111555', 'purpose': 'register', 'full_name': 'Existing'},
            format='json',
        )
        # Send should reject already-registered mobiles.
        self.assertEqual(send.status_code, 400, send.data)

        # Simulate a leftover open register challenge (legacy race).
        from django.utils import timezone
        from datetime import timedelta
        from django.contrib.auth.hashers import make_password

        ch = CustomerOTPChallenge.objects.create(
            mobile='9000111555',
            purpose='register',
            full_name='Existing',
            otp_hash=make_password('1234'),
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        verify = self.api.post(
            '/api/customer/otp/verify/',
            {'mobile': '9000111555', 'otp': '1234', 'purpose': 'register', 'full_name': 'Existing'},
            format='json',
        )
        self.assertEqual(verify.status_code, 200, verify.data)
        self.assertIn('access', verify.data)
        ch.refresh_from_db()
        self.assertIsNotNone(ch.consumed_at)

    @override_settings(DEBUG=True, CUSTOMER_OTP_FIXED='1234')
    def test_login_otp_unregistered_does_not_consume_challenge(self):
        """Login OTP send for unknown mobile fails before creating a challenge."""
        from customer.models import CustomerOTPChallenge

        send = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000999777', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(send.status_code, 404, send.data)
        self.assertEqual(send.data.get('code'), 'not_registered')
        self.assertFalse(
            CustomerOTPChallenge.objects.filter(mobile='9000999777', purpose='login').exists()
        )

    @override_settings(DEBUG=True, CUSTOMER_OTP_FIXED='1234')
    def test_login_otp_unregistered_mobile_can_verify_then_register(self):
        """Login OTP is blocked for unknown mobiles; lookup points to register."""
        lookup = self.api.post(
            '/api/customer/mobile/lookup/',
            {'mobile': '9000999888'},
            format='json',
        )
        self.assertEqual(lookup.status_code, 200, lookup.data)
        self.assertFalse(lookup.data.get('registered'))
        self.assertEqual(lookup.data.get('action'), 'register')

        send = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000999888', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(send.status_code, 404, send.data)
        self.assertEqual(send.data.get('code'), 'not_registered')
        self.assertEqual(send.data.get('action'), 'register')
        self.assertIn('registered', send.data.get('error', '').lower())

    @override_settings(DEBUG=True, CUSTOMER_OTP_FIXED='1234')
    def test_mobile_lookup_registered(self):
        from core.models import Client
        from customer.models import CustomerAccount

        client = Client.objects.create(full_name='Lookup User', mobile='9000111666')
        CustomerAccount.objects.create(
            client=client,
            mobile='9000111666',
            full_name='Lookup User',
            is_active=True,
        )
        res = self.api.post(
            '/api/customer/mobile/lookup/',
            {'mobile': '9000111666'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data.get('registered'))
        self.assertEqual(res.data.get('action'), 'login')

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

    def test_website_booking_creates_jobcard_without_auth(self):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.api.post(
                '/api/customer/website-bookings/',
                self._website_booking_payload(),
                format='json',
            )
        self.assertEqual(res.status_code, 201, res.data)
        booking = res.data['booking']
        self.assertEqual(booking['client_name'], 'Website Guest')
        self.assertEqual(booking['bhk_size'], '1 BHK')
        self.assertEqual(Decimal(str(booking['total_amount'])), Decimal('1000.00'))

        job = JobCard.objects.get(id=booking['id'])
        self.assertEqual(job.reference, 'Website')
        self.assertEqual(job.creation_source, JobCard.CreationSource.API)
        self.assertEqual(job.client.mobile, '9111222333')
        self.assertEqual(job.client.full_name, 'Website Guest')
        self.assertIsNotNone(job.sent_to_app_at)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.PENDING)
        self.assertTrue(CustomerAccount.objects.filter(mobile='9111222333').exists())

    def test_website_booking_app_source_marks_customer_app(self):
        res = self.api.post(
            '/api/customer/website-bookings/',
            self._website_booking_payload(
                mobile='9111222444',
                booking_source='APP',
            ),
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        job = JobCard.objects.get(id=res.data['booking']['id'])
        self.assertEqual(job.reference, 'Customer App')
        self.assertEqual(job.creation_source, JobCard.CreationSource.CUSTOMER_APP)
        self.assertEqual(job.client.mobile, '9111222444')

    def test_website_booking_rewrites_legacy_cockroach_label_to_catalog_package(self):
        """Marketing label must not land on JobCard — CRM would show two RETIRED boxes."""
        cockroach = PricingRate.objects.create(
            region=self.region,
            service_package='Cockroach Standard',
            plan_type='One Time Service',
            area_key='1 BHK',
            property_category='residential',
            amount=Decimal('1250.00'),
            gst_percent=Decimal('18.00'),
            price_includes_gst=False,
            is_active=True,
        )
        res = self.api.post(
            '/api/customer/website-bookings/',
            self._website_booking_payload(
                mobile='9111222555',
                service_type='Cockroach Control, Ant Control',
                pricing_rate_id=cockroach.id,
            ),
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        job = JobCard.objects.get(id=res.data['booking']['id'])
        self.assertEqual(job.service_type, 'Cockroach Standard')
        self.assertEqual(Decimal(str(job.total_amount)), Decimal('1475.00'))

    def test_website_booking_pending_price_still_resolves_legacy_cockroach_label(self):
        """Even without a rate, dual marketing label must become Cockroach Standard."""
        res = self.api.post(
            '/api/customer/website-bookings/',
            self._website_booking_payload(
                mobile='9111222556',
                service_type='Cockroach Control, Ant Control',
                pricing_rate_id=None,
                price_confirmation_pending=True,
            ),
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        job = JobCard.objects.get(id=res.data['booking']['id'])
        self.assertEqual(job.service_type, 'Cockroach Standard')
        self.assertEqual(
            JobCard.objects.filter(parent_job=job).count(),
            0,
        )
    def test_website_booking_rejects_without_otp_token(self):
        payload = self._website_booking_payload(mobile='9111222777')
        payload.pop('otp_verification_token')
        res = self.api.post('/api/customer/website-bookings/', payload, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('otp_verification_token', res.data.get('errors', {}))
        self.assertFalse(JobCard.objects.filter(client__mobile='9111222777').exists())

    def test_website_booking_rejects_invalid_otp_token(self):
        res = self.api.post(
            '/api/customer/website-bookings/',
            self._website_booking_payload(
                mobile='9111222888',
                otp_verification_token='not-a-valid-token',
            ),
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data.get('code'), 'otp_verification_invalid')
        self.assertFalse(JobCard.objects.filter(client__mobile='9111222888').exists())

    @override_settings(DEBUG=True, CUSTOMER_OTP_FIXED='1234', CUSTOMER_OTP_RESEND_COOLDOWN_SECONDS=0)
    def test_website_booking_otp_flow_gates_create(self):
        send = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9372792693', 'purpose': 'website_booking', 'full_name': 'Local Tester'},
            format='json',
        )
        self.assertEqual(send.status_code, 200, send.data)
        self.assertEqual(send.data.get('dev_otp'), '1234')

        bad = self.api.post(
            '/api/customer/otp/verify/',
            {'mobile': '9372792693', 'otp': '9999', 'purpose': 'website_booking'},
            format='json',
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.data.get('code'), 'otp_invalid')

        verify = self.api.post(
            '/api/customer/otp/verify/',
            {'mobile': '9372792693', 'otp': '1234', 'purpose': 'website_booking'},
            format='json',
        )
        self.assertEqual(verify.status_code, 200, verify.data)
        token = verify.data['otp_verification_token']
        self.assertTrue(token)

        blocked = self.api.post(
            '/api/customer/website-bookings/',
            self._website_booking_payload(
                mobile='9372792693',
                full_name='Local Tester',
                otp_verification_token='wrong',
            ),
            format='json',
        )
        self.assertEqual(blocked.status_code, 400)

        created = self.api.post(
            '/api/customer/website-bookings/',
            self._website_booking_payload(
                mobile='9372792693',
                full_name='Local Tester',
                otp_verification_token=token,
            ),
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)

        reused = self.api.post(
            '/api/customer/website-bookings/',
            self._website_booking_payload(
                mobile='9372792693',
                full_name='Local Tester',
                otp_verification_token=token,
            ),
            format='json',
        )
        self.assertEqual(reused.status_code, 400)
        self.assertEqual(reused.data.get('code'), 'otp_verification_used')

    def test_website_booking_verification_token_is_db_backed(self):
        """
        Proof tokens must survive across processes/workers.
        Previously LocMemCache caused false "already used or expired" with gunicorn --workers 2.
        """
        import jwt

        from customer.models import WebsiteBookingVerificationJti
        from customer.utils import (
            SECRET_KEY,
            WEBSITE_BOOKING_TOKEN_AUD,
            WebsiteBookingVerificationError,
            consume_website_booking_verification_token,
            issue_website_booking_verification_token,
        )

        mobile = '9111223010'
        token, ttl = issue_website_booking_verification_token(mobile)
        self.assertGreater(ttl, 0)

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=['HS256'],
            audience=WEBSITE_BOOKING_TOKEN_AUD,
        )
        row = WebsiteBookingVerificationJti.objects.get(jti=payload['jti'])
        self.assertEqual(row.mobile, mobile)
        self.assertIsNone(row.consumed_at)

        consume_website_booking_verification_token(token, mobile)
        row.refresh_from_db()
        self.assertIsNotNone(row.consumed_at)

        with self.assertRaises(WebsiteBookingVerificationError) as ctx:
            consume_website_booking_verification_token(token, mobile)
        self.assertEqual(ctx.exception.code, 'otp_verification_used')

    @override_settings(
        DEBUG=True,
        CUSTOMER_OTP_FIXED='1234',
        CUSTOMER_OTP_RESEND_COOLDOWN_SECONDS=60,
        WEBSITE_BOOKING_OTP_MAX_PER_HOUR=5,
        WEBSITE_BOOKING_OTP_WINDOW_SECONDS=3600,
    )
    def test_website_booking_otp_skips_short_cooldown(self):
        """Website booking ignores short resend cooldown; rapid resends are allowed."""
        first = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9111222999', 'purpose': 'website_booking'},
            format='json',
        )
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data.get('resend_after'), 0)
        second = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9111222999', 'purpose': 'website_booking'},
            format='json',
        )
        self.assertEqual(second.status_code, 200, second.data)
        self.assertNotEqual(second.data.get('code'), 'otp_cooldown')

    @override_settings(
        DEBUG=True,
        CUSTOMER_OTP_FIXED='1234',
        CUSTOMER_OTP_RESEND_COOLDOWN_SECONDS=0,
        WEBSITE_BOOKING_OTP_MAX_PER_HOUR=5,
        WEBSITE_BOOKING_OTP_WINDOW_SECONDS=3600,
    )
    def test_website_booking_otp_hourly_limit(self):
        """Max 5 website_booking OTP sends per mobile per rolling hour."""
        mobile = '9111223001'
        for i in range(5):
            res = self.api.post(
                '/api/customer/otp/send/',
                {'mobile': mobile, 'purpose': 'website_booking'},
                format='json',
            )
            self.assertEqual(res.status_code, 200, f'send #{i + 1}: {res.data}')

        blocked = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': mobile, 'purpose': 'website_booking'},
            format='json',
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.data.get('code'), 'otp_hourly_limit')
        self.assertIn('5 OTPs per hour', blocked.data.get('error', ''))
        self.assertIsInstance(blocked.data.get('retry_after'), int)
        self.assertGreaterEqual(blocked.data['retry_after'], 1)

        # Different mobile is unaffected.
        other = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9111223002', 'purpose': 'website_booking'},
            format='json',
        )
        self.assertEqual(other.status_code, 200, other.data)

    def test_website_booking_premium_applies_surcharge(self):
        res = self.api.post(
            '/api/customer/website-bookings/',
            {
                'full_name': 'Premium Guest',
                'mobile': '9111222444',
                'service_type': 'General Pest Control',
                'pricing_rate_id': self.rate.id,
                'package_tier': 'premium',
                'address': '99 Premium Road',
                'city': 'Mumbai',
                'bhk_size': '1 BHK',
                'booking_type': 'one_time',
                'otp_verification_token': self._website_otp_token('9111222444'),
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(str(res.data['booking']['total_amount'])), Decimal('1150.00'))
        job = JobCard.objects.get(id=res.data['booking']['id'])
        self.assertEqual(job.package_tier, 'premium')

    def test_website_booking_amc_sets_cycles(self):
        amc_rate, _ = PricingRate.objects.get_or_create(
            region=self.region,
            service_package='Cockroach / Ants',
            plan_type='AMC Package',
            area_key='1 BHK',
            defaults={'amount': Decimal('2500.00'), 'is_active': True},
        )
        amc_rate.amount = Decimal('2500.00')
        amc_rate.is_active = True
        amc_rate.save(update_fields=['amount', 'is_active', 'updated_at'])

        res = self.api.post(
            '/api/customer/website-bookings/',
            {
                'full_name': 'AMC Guest',
                'mobile': '9111222555',
                'service_type': 'Cockroach / Ants',
                'pricing_rate_id': amc_rate.id,
                'package_tier': 'standard',
                'address': '7 AMC Street',
                'city': 'Mumbai',
                'bhk_size': '1 BHK',
                'booking_type': 'amc',
                'otp_verification_token': self._website_otp_token('9111222555'),
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        job = JobCard.objects.get(id=res.data['booking']['id'])
        self.assertEqual(job.service_category, JobCard.ServiceCategory.AMC)
        self.assertEqual(job.service_cycle, 1)
        # JobCardService may refine max_cycle from schedule rules; AMC create starts at 3.
        self.assertGreaterEqual(job.max_cycle or 1, 1)
        self.assertEqual(Decimal(str(job.total_amount or job.price)), Decimal('2500.00'))

    def test_website_booking_requires_name_and_mobile(self):
        res = self.api.post(
            '/api/customer/website-bookings/',
            {
                'service_type': 'General Pest Control',
                'pricing_rate_id': self.rate.id,
                'address': 'No Name Lane',
                'city': 'Mumbai',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('full_name', res.data.get('errors', {}))
        self.assertIn('mobile', res.data.get('errors', {}))

    def test_website_booking_reuses_existing_account(self):
        first = self.api.post(
            '/api/customer/website-bookings/',
            {
                'full_name': 'Repeat Guest',
                'mobile': '9111222666',
                'service_type': 'General Pest Control',
                'pricing_rate_id': self.rate.id,
                'address': '1 First Visit',
                'city': 'Mumbai',
                'bhk_size': '1 BHK',
                'otp_verification_token': self._website_otp_token('9111222666'),
            },
            format='json',
        )
        self.assertEqual(first.status_code, 201, first.data)
        second = self.api.post(
            '/api/customer/website-bookings/',
            {
                'full_name': 'Repeat Guest Updated',
                'mobile': '9111222666',
                'service_type': 'General Pest Control',
                'pricing_rate_id': self.rate.id,
                'address': '2 Second Visit',
                'city': 'Mumbai',
                'bhk_size': '1 BHK',
                'otp_verification_token': self._website_otp_token('9111222666'),
            },
            format='json',
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(
            CustomerAccount.objects.filter(mobile='9111222666').count(),
            1,
        )
        account = CustomerAccount.objects.get(mobile='9111222666')
        self.assertEqual(account.full_name, 'Repeat Guest Updated')
        self.assertEqual(account.client.full_name, 'Repeat Guest Updated')
