"""Acceptance tests: silent Website Booking Form → Website Lead (Inquiry) capture."""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Inquiry, JobCard, PricingRate, PricingRegion
from customer.utils import issue_website_booking_verification_token


@override_settings(
    TELEGRAM_NOTIFICATIONS_ENABLED=False,
    WEBSITE_LEAD_STAFF_WHATSAPP_ENABLED=False,
)
class WebsiteBookingInquiryUpsertTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.session_id = 'test-session-aaaa-bbbb-cccc-ddddeeee'

    def _upsert(self, **overrides):
        payload = {
            'booking_session_id': self.session_id,
            'mobile': '9876501234',
            'name': '',
            'city': '',
            'service_interest': '',
            'message': '',
            'remark': 'Lead source: Website Booking Form',
        }
        payload.update(overrides)
        return self.api.post('/api/inquiries/upsert/', payload, format='json')

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_1_valid_mobile_creates_inquiry(self, _tg):
        res = self._upsert(mobile='9876501234')
        self.assertEqual(res.status_code, 201, res.data)
        lead = Inquiry.objects.get(pk=res.data['id'])
        self.assertEqual(lead.mobile, '9876501234')
        self.assertEqual(lead.status, Inquiry.InquiryStatus.NEW)
        self.assertEqual(lead.booking_session_id, self.session_id)
        self.assertIn('Website Booking Form', lead.remark or '')

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_2_mobile_only_no_other_fields(self, tg_mock):
        res = self._upsert(
            mobile='9876501111',
            name='',
            city='',
            service_interest='',
            message='',
            premise_type='',
            premise_size='',
        )
        self.assertEqual(res.status_code, 201, res.data)
        lead = Inquiry.objects.get(pk=res.data['id'])
        self.assertEqual(lead.mobile, '9876501111')
        self.assertTrue(lead.name)
        self.assertTrue(lead.message)
        self.assertTrue(lead.service_interest)
        tg_mock.assert_called_once()
        self.assertEqual(tg_mock.call_args.kwargs['mobile'], '9876501111')

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_4_change_number_updates_same_session_no_duplicate(self, tg_mock):
        first = self._upsert(mobile='9876502222')
        self.assertEqual(first.status_code, 201, first.data)
        tg_mock.assert_called_once()
        second = self._upsert(mobile='9876503333', name='Updated Name')
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(Inquiry.objects.filter(booking_session_id=self.session_id).count(), 1)
        lead = Inquiry.objects.get(pk=first.data['id'])
        self.assertEqual(lead.mobile, '9876503333')
        self.assertEqual(lead.name, 'Updated Name')
        # Mobile changed on the same session — staff get a fresh Telegram.
        self.assertEqual(tg_mock.call_count, 2)
        self.assertEqual(tg_mock.call_args.kwargs['mobile'], '9876503333')

    def test_5_invalid_mobile_rejected(self):
        res = self._upsert(mobile='12345')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Inquiry.objects.count(), 0)

        res2 = self._upsert(mobile='abcdefghij')
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(Inquiry.objects.count(), 0)

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_6_refresh_same_session_no_duplicate(self, _tg):
        a = self._upsert(mobile='9876504444')
        b = self._upsert(mobile='9876504444', name='After Refresh')
        self.assertEqual(a.status_code, 201)
        self.assertEqual(b.status_code, 200)
        self.assertEqual(a.data['id'], b.data['id'])
        self.assertEqual(Inquiry.objects.filter(booking_session_id=self.session_id).count(), 1)

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_upsert_without_name_then_with_name_updates(self, tg_mock):
        """Mobile-only create notifies immediately; later name upgrades same lead once."""
        first = self._upsert(mobile='9876508888', name='')
        self.assertEqual(first.status_code, 201, first.data)
        lead = Inquiry.objects.get(pk=first.data['id'])
        self.assertEqual(lead.name, 'Website Lead')
        # Staff get the inquiry as soon as a valid mobile is captured.
        tg_mock.assert_called_once()
        self.assertEqual(tg_mock.call_args.kwargs['name'], 'Website Lead')
        self.assertEqual(tg_mock.call_args.kwargs['mobile'], '9876508888')

        second = self._upsert(mobile='9876508888', name='Priya Sharma')
        self.assertEqual(second.status_code, 200, second.data)
        lead.refresh_from_db()
        self.assertEqual(lead.name, 'Priya Sharma')
        # Same session — no duplicate Telegram spam on name fill.
        tg_mock.assert_called_once()

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_create_with_name_uses_real_name_and_notifies(self, tg_mock):
        res = self._upsert(mobile='9876509999', name='Anuj Shukla')
        self.assertEqual(res.status_code, 201, res.data)
        lead = Inquiry.objects.get(pk=res.data['id'])
        self.assertEqual(lead.name, 'Anuj Shukla')
        tg_mock.assert_called_once()
        self.assertEqual(tg_mock.call_args.kwargs['name'], 'Anuj Shukla')

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_placeholder_name_does_not_overwrite_real_name(self, tg_mock):
        first = self._upsert(mobile='9876507770', name='Rachna Rai')
        self.assertEqual(first.status_code, 201, first.data)
        tg_mock.assert_called_once()

        # Later silent upsert with empty name must not clobber the real name.
        second = self._upsert(mobile='9876507770', name='', service_interest='Cockroach / Ants')
        self.assertEqual(second.status_code, 200, second.data)
        lead = Inquiry.objects.get(pk=first.data['id'])
        self.assertEqual(lead.name, 'Rachna Rai')
        self.assertEqual(lead.service_interest, 'Cockroach / Ants')
        # No second notify — name was never a placeholder.
        tg_mock.assert_called_once()

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_explicit_website_lead_payload_does_not_stick_after_real_name(self, tg_mock):
        first = self._upsert(mobile='9876506660', name='Website Lead')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(Inquiry.objects.get(pk=first.data['id']).name, 'Website Lead')
        tg_mock.assert_called_once()

        second = self._upsert(mobile='9876506660', name='Website Lead')
        self.assertEqual(second.status_code, 200)
        # Repeat placeholder upsert must not re-notify.
        tg_mock.assert_called_once()

        third = self._upsert(mobile='9876506660', name='Karan Mehta')
        self.assertEqual(third.status_code, 200, third.data)
        lead = Inquiry.objects.get(pk=first.data['id'])
        self.assertEqual(lead.name, 'Karan Mehta')
        # Name upgrade updates CRM only — still a single create-time alert.
        tg_mock.assert_called_once()

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_name_with_digits_sanitized_on_upsert(self, tg_mock):
        """Digits in name are stripped; silent lead still creates + notifies."""
        res = self._upsert(mobile='9876502020', name='Ravi123 Kumar')
        self.assertEqual(res.status_code, 201, res.data)
        lead = Inquiry.objects.get(pk=res.data['id'])
        self.assertEqual(lead.name, 'Ravi Kumar')
        tg_mock.assert_called_once()

    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_mobile_only_create_notifies_once_per_session(self, tg_mock):
        """Debounced re-upserts with the same mobile must not spam Telegram."""
        first = self._upsert(mobile='9876501010', name='')
        self.assertEqual(first.status_code, 201, first.data)
        tg_mock.assert_called_once()

        # Same fingerprint-ish payload (mobile only) — update path, no new notify.
        second = self._upsert(mobile='9876501010', name='')
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data['id'], second.data['id'])
        tg_mock.assert_called_once()
        self.assertEqual(Inquiry.objects.filter(booking_session_id=self.session_id).count(), 1)


@override_settings(
    TELEGRAM_NOTIFICATIONS_ENABLED=False,
    WEBSITE_LEAD_STAFF_WHATSAPP_ENABLED=False,
    REVENUE_MODEL_V2=True,
)
class WebsiteBookingInquiryLinkTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.session_id = 'book-session-1111-2222-3333-44445555'
        self.region, _ = PricingRegion.objects.get_or_create(
            slug='inquiry-link-test-region',
            defaults={
                'name': 'Inquiry Link Test Region',
                'is_default': True,
                'is_active': True,
            },
        )
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

    def _otp_token(self, mobile='9876505555'):
        token, _ = issue_website_booking_verification_token(mobile)
        return token

    def _booking_payload(self, **overrides):
        mobile = overrides.get('mobile', '9876505555')
        payload = {
            'full_name': 'Booking Customer',
            'mobile': mobile,
            'service_type': 'General Pest Control',
            'package_tier': 'standard',
            'property_type': 'Home / Flat',
            'bhk_size': '1 BHK',
            'address': 'Andheri West, Mumbai',
            'full_address': 'Andheri West, Mumbai',
            'city': 'Mumbai',
            'booking_type': 'one_time',
            'pricing_rate_id': self.rate.id,
            'booking_date': '2026-09-16',
            'booking_time': '11:00',
            'timezone': 'Asia/Kolkata',
            'time_slot': '11:00 am',
            'otp_verification_token': self._otp_token(mobile),
            'booking_session_id': self.session_id,
        }
        payload.update(overrides)
        if 'otp_verification_token' not in overrides:
            payload['otp_verification_token'] = self._otp_token(payload['mobile'])
        return payload

    @patch('core.services.notify_new_inquiry', return_value=True)
    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_3_full_form_confirm_links_one_inquiry_one_booking(self, _partner, _tg):
        upsert = self.api.post(
            '/api/inquiries/upsert/',
            {
                'booking_session_id': self.session_id,
                'mobile': '9876505555',
                'name': 'Booking Customer',
                'city': 'Mumbai',
                'service_interest': 'Cockroach / Ants',
                'message': 'Quote request from website home page.',
                'premise_type': 'residential',
                'premise_size': '2bhk',
                'service_frequency': 'one-time',
                'remark': 'Lead source: Website Booking Form',
            },
            format='json',
        )
        self.assertEqual(upsert.status_code, 201, upsert.data)
        inquiry_id = upsert.data['id']

        book = self.api.post(
            '/api/customer/website-bookings/',
            self._booking_payload(inquiry_id=inquiry_id),
            format='json',
        )
        self.assertEqual(book.status_code, 201, book.data)
        self.assertEqual(Inquiry.objects.filter(booking_session_id=self.session_id).count(), 1)
        self.assertEqual(JobCard.objects.count(), 1)

        lead = Inquiry.objects.get(pk=inquiry_id)
        job = JobCard.objects.get()
        self.assertEqual(lead.status, Inquiry.InquiryStatus.CONVERTED)
        self.assertEqual(lead.linked_jobcard_id, job.id)

        # Second booking for same session must not create another inquiry
        book2 = self.api.post(
            '/api/customer/website-bookings/',
            self._booking_payload(mobile='9876505555'),
            format='json',
        )
        self.assertEqual(book2.status_code, 201, book2.data)
        self.assertEqual(Inquiry.objects.filter(booking_session_id=self.session_id).count(), 1)

    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_7_inquiry_api_fail_booking_still_works(self, _partner):
        payload = self._booking_payload(
            mobile='9876506666',
            booking_session_id='',
            inquiry_id=None,
        )
        book = self.api.post('/api/customer/website-bookings/', payload, format='json')
        self.assertEqual(book.status_code, 201, book.data)
        self.assertEqual(JobCard.objects.count(), 1)
        self.assertEqual(Inquiry.objects.count(), 0)

    @patch('core.services.notify_new_inquiry', return_value=True)
    @patch('partner.services.schedule_auto_send_new_booking_to_partner_app')
    def test_booking_failure_does_not_mark_inquiry_converted(self, _partner, _tg):
        upsert = self.api.post(
            '/api/inquiries/upsert/',
            {
                'booking_session_id': self.session_id,
                'mobile': '9876507777',
                'name': 'Fail Case',
                'city': 'Mumbai',
                'service_interest': 'General Pest Control',
                'message': 'Auto-captured from Website Booking Form.',
            },
            format='json',
        )
        self.assertEqual(upsert.status_code, 201, upsert.data)

        bad = self.api.post(
            '/api/customer/website-bookings/',
            self._booking_payload(
                mobile='9876507777',
                otp_verification_token='not-a-valid-token',
            ),
            format='json',
        )
        self.assertEqual(bad.status_code, 400)
        lead = Inquiry.objects.get(pk=upsert.data['id'])
        self.assertEqual(lead.status, Inquiry.InquiryStatus.NEW)
        self.assertIsNone(lead.linked_jobcard_id)
