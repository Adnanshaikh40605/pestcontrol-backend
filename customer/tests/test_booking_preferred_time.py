"""Preferred booking time window — coerce overnight starts to 08:00."""

from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from core.models import PricingRate, PricingRegion, JobCard
from customer.models import CustomerAccount
from customer.serializers import (
    EARLIEST_BOOKABLE_HOUR,
    WebsiteBookSerializer,
    coerce_bookable_wall_time,
)
from customer.utils import issue_website_booking_verification_token


class CoerceBookableWallTimeTests(SimpleTestCase):
    def test_midnight_and_early_morning_coerce_to_eight(self):
        cases = [(0, 0), (2, 0), (5, 30), (7, 59)]
        for hour, minute in cases:
            with self.subTest(hour=hour, minute=minute):
                h, m, coerced = coerce_bookable_wall_time(hour, minute)
                self.assertTrue(coerced)
                self.assertEqual(h, EARLIEST_BOOKABLE_HOUR)
                self.assertEqual(m, 0)

    def test_eight_am_and_daytime_unchanged(self):
        for hour, minute in [(8, 0), (9, 0), (14, 0), (19, 30)]:
            with self.subTest(hour=hour, minute=minute):
                h, m, coerced = coerce_bookable_wall_time(hour, minute)
                self.assertFalse(coerced)
                self.assertEqual((h, m), (hour, minute))


@override_settings(REVENUE_MODEL_V2=True)
class WebsiteBookingNightTimeCoercionTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.region, _ = PricingRegion.objects.get_or_create(
            slug='preferred-time-test-region',
            defaults={
                'name': 'Preferred Time Test Region',
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

    def _token(self, mobile: str) -> str:
        token, _ = issue_website_booking_verification_token(mobile)
        return token

    def _payload(self, mobile: str, **overrides):
        payload = {
            'full_name': 'Night Guest',
            'mobile': mobile,
            'service_type': 'General Pest Control',
            'pricing_rate_id': self.rate.id,
            'package_tier': 'standard',
            'address': '42 Night Lane',
            'city': 'Mumbai',
            'bhk_size': '1 BHK',
            'property_type': 'Home / Flat',
            'booking_type': 'one_time',
            'booking_date': '2026-09-20',
            'booking_time': '02:00',
            'timezone': 'Asia/Kolkata',
            'time_slot': '2:00 AM',
            'otp_verification_token': self._token(mobile),
        }
        payload.update(overrides)
        if 'otp_verification_token' not in overrides and 'mobile' in overrides:
            payload['otp_verification_token'] = self._token(overrides['mobile'])
        return payload

    def test_serializer_coerces_night_booking_time_to_eight(self):
        mobile = '9111222401'
        serializer = WebsiteBookSerializer(data=self._payload(mobile))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        data = serializer.validated_data
        self.assertEqual(data['booking_time'], '08:00')
        self.assertEqual(data['time_slot'], '8:00 AM')
        sched = data['schedule_datetime']
        self.assertEqual(sched.hour, 8)
        self.assertEqual(sched.minute, 0)
        self.assertEqual(sched.date(), date(2026, 9, 20))

    def test_serializer_keeps_afternoon_booking_time(self):
        mobile = '9111222402'
        serializer = WebsiteBookSerializer(
            data=self._payload(
                mobile,
                booking_time='15:00',
                time_slot='3:00 PM',
            )
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        data = serializer.validated_data
        self.assertEqual(data['booking_time'], '15:00')
        self.assertEqual(data['schedule_datetime'].hour, 15)

    def test_website_booking_persists_coerced_eight_am(self):
        mobile = '9111222403'
        with self.captureOnCommitCallbacks(execute=True):
            res = self.api.post(
                '/api/customer/website-bookings/',
                self._payload(
                    mobile,
                    full_name='Persist Night',
                    address='99 Early Lane',
                    booking_date='2026-09-21',
                    booking_time='05:30',
                    time_slot='5:30 AM',
                ),
                format='json',
            )
        self.assertEqual(res.status_code, 201, res.data)
        job = JobCard.objects.get(id=res.data['booking']['id'])
        ist = job.schedule_datetime.astimezone(ZoneInfo('Asia/Kolkata'))
        self.assertEqual(ist.hour, 8)
        self.assertEqual(ist.minute, 0)
        self.assertEqual(job.time_slot, '8:00 AM')
        self.assertTrue(CustomerAccount.objects.filter(mobile=mobile).exists())
