"""pc99_booking_confirmation WhatsApp on booking confirm (website / app / CRM)."""
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State
from core.services import JobCardService
from core.whatsflow_pc99 import (
    BOOKING_CONFIRMATION_TEMPLATE_DEFAULT,
    build_booking_confirmation_params,
    notify_booking_confirmation,
)
from customer.utils import issue_website_booking_verification_token


@override_settings(
    BOOKING_CONFIRMATION_WHATSAPP_ENABLED=True,
    BOOKING_CONFIRMATION_WHATSAPP_TEMPLATE='pc99_booking_confirmation',
    BOOKING_CONFIRMATION_WHATSAPP_TERMS='Standard service terms apply.',
    WHATSFLOW_API_KEY='wf_test',
)
class BookingConfirmationHelperTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(
            full_name='Rahul Sharma',
            mobile='9876543210',
        )
        country, _ = Country.objects.get_or_create(name='India WA Test')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra WA')
        self.city, _ = City.objects.get_or_create(state=state, name='Pune WA')
        norm = Location.normalize_text('Kothrud')
        self.location, _ = Location.objects.get_or_create(
            city=self.city,
            normalized_name=norm,
            defaults={'name': 'Kothrud'},
        )
        self.schedule = datetime(2026, 8, 5, 4, 30, tzinfo=dt_timezone.utc)  # 10:00 IST

    def _job(self, **kwargs):
        fields = {
            'client': self.client_record,
            'service_type': 'Cockroach Control',
            'schedule_datetime': self.schedule,
            'time_slot': '10:00 AM',
            'price': '2500',
            'total_amount': Decimal('2500.00'),
            'status': JobCard.JobStatus.PENDING,
            'master_location': self.location,
            'city': 'Pune',
            'reference': 'Website',
        }
        fields.update(kwargs)
        return JobCard.objects.create(**fields)

    def test_build_params_match_approved_template_order(self):
        job = self._job()
        # code is set on save from pk
        job.refresh_from_db()
        params = build_booking_confirmation_params(job)
        self.assertEqual(len(params), 8)
        self.assertEqual(params[0], 'Rahul Sharma')
        self.assertEqual(params[1], str(job.code))
        self.assertEqual(params[2], 'Cockroach Control')
        self.assertEqual(params[3], 'Kothrud')
        self.assertEqual(params[4], '05 Aug 2026')
        self.assertEqual(params[5], '10:00 AM')
        self.assertEqual(params[6], '2500')
        self.assertEqual(params[7], 'Standard service terms apply.')

    @patch('core.whatsflow_pc99.send_template_by_phone')
    def test_notify_sends_exact_template_name_and_body_params(self, send):
        send.return_value = {'ok': True, 'message_id': 'wamid.TEST', 'error': ''}
        job = self._job()
        job.refresh_from_db()
        result = notify_booking_confirmation(job)
        self.assertTrue(result['ok'])
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['template_name'], BOOKING_CONFIRMATION_TEMPLATE_DEFAULT)
        self.assertEqual(kwargs['template_name'], 'pc99_booking_confirmation')
        self.assertEqual(kwargs['phone'], '9876543210')
        self.assertEqual(kwargs['body_params'], build_booking_confirmation_params(job))
        self.assertEqual(kwargs['external_id'], f'booking-confirmation:{job.pk}')

    @patch('core.whatsflow_pc99.send_template_by_phone')
    def test_skips_draft_without_price(self, send):
        job = self._job(price='', total_amount=Decimal('0.00'))
        result = notify_booking_confirmation(job)
        self.assertTrue(result.get('skipped'))
        send.assert_not_called()

    @patch('core.whatsflow_pc99.send_template_by_phone')
    def test_soft_fail_returns_error_dict(self, send):
        send.return_value = {'ok': False, 'message_id': '', 'error': 'meta_timeout'}
        job = self._job()
        result = notify_booking_confirmation(job)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'meta_timeout')


@override_settings(
    BOOKING_CONFIRMATION_WHATSAPP_ENABLED=True,
    BOOKING_CONFIRMATION_WHATSAPP_TEMPLATE='pc99_booking_confirmation',
    WHATSFLOW_API_KEY='wf_test',
)
class BookingConfirmationCreateHookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='crm_wa', password='pass1234')
        self.client_record = Client.objects.create(full_name='CRM Guest', mobile='9123456780')
        self.schedule = timezone.now() + timedelta(days=2)

    @patch('core.whatsflow_pc99.send_template_by_phone')
    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_crm_create_with_price_schedules_confirmation(self, _partner, send):
        send.return_value = {'ok': True, 'message_id': 'wamid.CRM', 'error': ''}
        with self.captureOnCommitCallbacks(execute=True):
            job = JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Cockroach Control',
                    'schedule_datetime': self.schedule,
                    'time_slot': '10:00 AM',
                    'price': '2500',
                    'city': 'Pune',
                    'reference': 'Poster',
                    'status': JobCard.JobStatus.PENDING,
                },
                user=self.user,
            )
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['template_name'], 'pc99_booking_confirmation')
        self.assertEqual(kwargs['body_params'][0], 'CRM Guest')
        self.assertEqual(kwargs['body_params'][1], str(job.code))
        self.assertEqual(kwargs['body_params'][2], 'Cockroach Control')
        self.assertEqual(kwargs['body_params'][6], '2500')
        self.assertEqual(kwargs['body_params'][7], 'Standard service terms apply.')

    @patch('core.whatsflow_pc99.send_template_by_phone')
    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_draft_inquiry_style_create_skips_whatsapp(self, _partner, send):
        with self.captureOnCommitCallbacks(execute=True):
            JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Cockroach Control',
                    'schedule_datetime': self.schedule,
                    'price': '',
                    'reference': 'CRM Inquiry',
                    'status': JobCard.JobStatus.PENDING,
                    'notes': '[Draft from inquiry — staff must confirm final price/details before WhatsApp]',
                },
                user=self.user,
            )
        send.assert_not_called()


@override_settings(
    BOOKING_CONFIRMATION_WHATSAPP_ENABLED=True,
    BOOKING_CONFIRMATION_WHATSAPP_TEMPLATE='pc99_booking_confirmation',
    WHATSFLOW_API_KEY='wf_test',
)
class BookingConfirmationCrmPriceConfirmTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='crm_price', password='pass1234')
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_record = Client.objects.create(full_name='Draft Customer', mobile='9000111222')
        self.job = JobCard.objects.create(
            client=self.client_record,
            service_type='Termite Control',
            schedule_datetime=timezone.now() + timedelta(days=3),
            time_slot='11:00 AM',
            price='',
            total_amount=Decimal('0.00'),
            status=JobCard.JobStatus.PENDING,
            reference='Website',
            city='Pune',
        )

    @patch('core.whatsflow_pc99.send_template_by_phone')
    def test_price_confirm_on_edit_sends_template(self, send):
        send.return_value = {'ok': True, 'message_id': 'wamid.EDIT', 'error': ''}
        with self.captureOnCommitCallbacks(execute=True):
            res = self.api.patch(
                f'/api/v1/jobcards/{self.job.id}/',
                {'price': '3200', 'total_amount': '3200.00'},
                format='json',
            )
        self.assertEqual(res.status_code, 200, res.data)
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['template_name'], 'pc99_booking_confirmation')
        self.assertEqual(kwargs['body_params'][0], 'Draft Customer')
        self.assertEqual(kwargs['body_params'][6], '3200')

    @patch('core.whatsflow_pc99.send_template_by_phone')
    def test_price_change_after_confirm_does_not_resend(self, send):
        self.job.price = '3200'
        self.job.total_amount = Decimal('3200.00')
        self.job.save(update_fields=['price', 'total_amount', 'updated_at'])
        with self.captureOnCommitCallbacks(execute=True):
            res = self.api.patch(
                f'/api/v1/jobcards/{self.job.id}/',
                {'price': '3500', 'total_amount': '3500.00'},
                format='json',
            )
        self.assertEqual(res.status_code, 200, res.data)
        send.assert_not_called()


@override_settings(
    BOOKING_CONFIRMATION_WHATSAPP_ENABLED=True,
    BOOKING_CONFIRMATION_WHATSAPP_TEMPLATE='pc99_booking_confirmation',
    WHATSFLOW_API_KEY='wf_test',
    DEBUG=True,
    CUSTOMER_OTP_FIXED='1234',
)
class WebsiteBookingConfirmationTests(TestCase):
    def setUp(self):
        from core.models import PricingRate, PricingRegion

        self.api = APIClient()
        self.region, _ = PricingRegion.objects.get_or_create(
            slug='wa-booking-region',
            defaults={'name': 'WA Booking Region', 'is_default': True, 'is_active': True},
        )
        self.region.is_default = True
        self.region.is_active = True
        self.region.save(update_fields=['is_default', 'is_active', 'updated_at'])
        self.rate, _ = PricingRate.objects.get_or_create(
            region=self.region,
            service_package='General Pest Control',
            plan_type='One Time Service',
            area_key='1 BHK',
            defaults={'amount': Decimal('1000.00'), 'is_active': True},
        )
        self.rate.amount = Decimal('1000.00')
        self.rate.is_active = True
        self.rate.save(update_fields=['amount', 'is_active', 'updated_at'])

    def _website_otp_token(self, mobile='9111222333'):
        token, _ = issue_website_booking_verification_token(mobile)
        return token

    @patch('core.whatsflow_pc99.send_template_by_phone')
    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_website_booking_sends_confirmation(self, _partner, send):
        send.return_value = {'ok': True, 'message_id': 'wamid.WEB', 'error': ''}
        payload = {
            'full_name': 'Website Guest',
            'mobile': '9111222333',
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
            'otp_verification_token': self._website_otp_token('9111222333'),
        }
        with self.captureOnCommitCallbacks(execute=True):
            res = self.api.post('/api/customer/website-bookings/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['template_name'], 'pc99_booking_confirmation')
        self.assertEqual(kwargs['body_params'][0], 'Website Guest')
        self.assertEqual(kwargs['body_params'][2], 'General Pest Control')
        self.assertEqual(kwargs['body_params'][5], '10:30 AM')
        self.assertEqual(kwargs['body_params'][6], '1000')
        self.assertEqual(len(kwargs['body_params']), 8)

    @patch('core.whatsflow_pc99.send_template_by_phone')
    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_customer_app_booking_sends_confirmation(self, _partner, send):
        send.return_value = {'ok': True, 'message_id': 'wamid.APP', 'error': ''}
        reg = self.api.post(
            '/api/customer/register/',
            {
                'full_name': 'App User 2',
                'mobile': '9888777111',
                'password': 'secret12',
            },
            format='json',
        )
        self.assertEqual(reg.status_code, 201, reg.data)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {reg.data['access']}")
        with self.captureOnCommitCallbacks(execute=True):
            book = self.api.post(
                '/api/customer/bookings/',
                {
                    'service_type': 'General Pest Control',
                    'pricing_rate_id': self.rate.id,
                    'package_tier': 'standard',
                    'address': '12 App Lane',
                    'city': 'Mumbai',
                    'bhk_size': '1 BHK',
                    'time_slot': '10:00 AM',
                },
                format='json',
            )
        self.assertEqual(book.status_code, 201, book.data)
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['template_name'], 'pc99_booking_confirmation')
        self.assertEqual(kwargs['body_params'][0], 'App User 2')
        self.assertEqual(kwargs['body_params'][6], '1000')
        self.assertEqual(len(kwargs['body_params']), 8)

    @patch('core.whatsflow_pc99.send_template_by_phone')
    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_whatsapp_failure_does_not_fail_website_booking(self, _partner, send):
        send.return_value = {'ok': False, 'message_id': '', 'error': 'meta_down'}
        payload = {
            'full_name': 'Soft Fail Guest',
            'mobile': '9111222444',
            'service_type': 'General Pest Control',
            'pricing_rate_id': self.rate.id,
            'package_tier': 'standard',
            'address': '99 Fail Lane',
            'city': 'Mumbai',
            'bhk_size': '1 BHK',
            'booking_type': 'one_time',
            'booking_date': '2026-09-21',
            'booking_time': '11:00',
            'timezone': 'Asia/Kolkata',
            'time_slot': '11:00 AM',
            'otp_verification_token': self._website_otp_token('9111222444'),
        }
        with self.captureOnCommitCallbacks(execute=True):
            res = self.api.post('/api/customer/website-bookings/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(JobCard.objects.filter(client__mobile='9111222444').exists())
        send.assert_called_once()
