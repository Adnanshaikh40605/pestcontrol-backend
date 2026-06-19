from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Technician
from core.roles import ensure_user_profile
from partner.models import Partner
from staff_tracking.identity import get_or_create_profile
from staff_tracking.models import TrackingProfile
from staff_tracking.services import check_in, check_out, record_ping


class StaffTrackingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tech = Technician.objects.create(name='Test Tech', mobile='9876543210', is_active=True)
        self.partner = Partner.objects.create(
            full_name='Test Tech',
            mobile='9876543210',
            role='technician',
            is_active=True,
            is_app_approved=True,
            core_technician=self.tech,
        )
        self.partner.set_password('testpass123')
        self.partner.save()
        self.profile = get_or_create_profile(self.tech, partner=self.partner)

        User = get_user_model()
        self.crm_user = User.objects.create_user(username='admintrack', password='adminpass123')
        ensure_user_profile(self.crm_user, 'admin')

    def _partner_token(self):
        from partner.utils import generate_partner_tokens
        return generate_partner_tokens(self.partner)['access']

    def _crm_token(self):
        return str(RefreshToken.for_user(self.crm_user).access_token)

    def test_checkin_checkout_and_ping(self):
        session = check_in(self.profile, latitude=18.75, longitude=73.40, accuracy_m=10)
        self.assertEqual(session.status, 'active')
        ping = record_ping(self.profile, latitude=18.751, longitude=73.401, accuracy_m=8)
        self.assertIsNotNone(ping.id)
        session = check_out(self.profile, latitude=18.752, longitude=73.402, accuracy_m=9)
        self.assertEqual(session.status, 'completed')

    def test_mobile_checkin_api(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self._partner_token()}')
        res = self.client.post(
            '/api/staff-tracking/attendance/checkin/',
            {'latitude': '18.7500000', 'longitude': '73.4000000', 'accuracy_m': 12},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_partner_without_core_technician_link_still_works(self):
        """Partner matched to Technician by mobile when core_technician unset."""
        self.partner.core_technician = None
        self.partner.save(update_fields=['core_technician'])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self._partner_token()}')
        res = self.client.get('/api/staff-tracking/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.partner.refresh_from_db()
        self.assertIsNotNone(self.partner.core_technician_id)

    def test_crm_live_api(self):
        check_in(self.profile, latitude=18.75, longitude=73.40)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self._crm_token()}')
        res = self.client.get('/api/staff-tracking/live/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) >= 1)

    def test_ping_rejected_without_checkin(self):
        TrackingProfile.objects.filter(pk=self.profile.pk).delete()
        fresh_profile = get_or_create_profile(self.tech, partner=self.partner)
        with self.assertRaises(ValueError):
            record_ping(fresh_profile, latitude=18.75, longitude=73.40)
