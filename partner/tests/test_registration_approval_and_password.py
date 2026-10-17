"""App self-registration stays pending, and password reset uses a one-time OTP."""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Technician
from partner.models import Partner


@override_settings(DEBUG=True)
class PartnerRegistrationApprovalTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.admin = User.objects.create_superuser(
            username='approvaladmin', email='a@x.com', password='pass12345'
        )

    def _assign_ids(self):
        self.api.force_authenticate(user=self.admin)
        res = self.api.get('/api/technicians/active/')
        self.assertEqual(res.status_code, 200, res.data)
        return [row['id'] for row in res.data]

    def test_new_app_registration_stays_pending_and_off_the_assign_list(self):
        desk = Technician.objects.create(name='Desk Tech', mobile='9800000090', is_active=True)
        res = self.api.post(
            '/api/partner/register/',
            {
                'full_name': 'New Tech',
                'mobile': '9800000091',
                'password': 'secret12',
                'role': 'technician',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertFalse(res.data['partner']['is_app_approved'])

        tech = Technician.objects.get(mobile='9800000091')
        partner = Partner.objects.get(mobile='9800000091')
        self.assertFalse(tech.is_active)
        self.assertFalse(partner.is_app_approved)
        self.assertTrue(partner.is_active)
        self.assertEqual(partner.core_technician_id, tech.id)
        self.assertNotIn(tech.id, self._assign_ids())
        self.assertIn(desk.id, self._assign_ids())

        approve = self.api.post(f'/api/technicians/{tech.id}/approve-partner-app/')
        self.assertEqual(approve.status_code, 200, approve.data)
        tech.refresh_from_db()
        partner.refresh_from_db()
        self.assertTrue(tech.is_active)
        self.assertTrue(partner.is_app_approved)
        self.assertIn(tech.id, self._assign_ids())

    def test_unapproved_partner_stays_out_even_if_the_technician_row_is_active(self):
        tech = Technician.objects.create(name='Waiting', mobile='9800000092', is_active=True)
        Partner.objects.create(
            full_name='Waiting',
            mobile='9800000092',
            password='hashed',
            core_technician=tech,
            is_active=True,
            is_app_approved=False,
        )
        self.assertNotIn(tech.id, self._assign_ids())


@override_settings(DEBUG=True, PARTNER_PASSWORD_OTP_MAX_PER_HOUR=5)
class PartnerPasswordResetTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.partner = Partner.objects.create(
            full_name='Reset Tech',
            mobile='9800000093',
            role=Partner.Role.TECHNICIAN,
            is_active=True,
            is_app_approved=True,
        )
        self.partner.set_password('oldpass1')
        self.partner.save(update_fields=['password'])

    def test_otp_resets_the_password_and_cannot_be_reused(self):
        sent = self.api.post('/api/partner/password/otp/', {'mobile': '9800000093'}, format='json')
        self.assertEqual(sent.status_code, 200, sent.data)
        self.assertEqual(sent.data['dev_otp'], '1234')

        wrong = self.api.post(
            '/api/partner/password/reset/',
            {'mobile': '9800000093', 'otp': '0000', 'new_password': 'newpass1'},
            format='json',
        )
        self.assertEqual(wrong.status_code, 400, wrong.data)
        self.partner.refresh_from_db()
        self.assertTrue(self.partner.check_password('oldpass1'))

        ok = self.api.post(
            '/api/partner/password/reset/',
            {'mobile': '9800000093', 'otp': '1234', 'new_password': 'newpass1'},
            format='json',
        )
        self.assertEqual(ok.status_code, 200, ok.data)
        self.partner.refresh_from_db()
        self.assertTrue(self.partner.check_password('newpass1'))
        self.assertFalse(self.partner.check_password('oldpass1'))

        reused = self.api.post(
            '/api/partner/password/reset/',
            {'mobile': '9800000093', 'otp': '1234', 'new_password': 'otherpass'},
            format='json',
        )
        self.assertEqual(reused.status_code, 400, reused.data)

        login = self.api.post(
            '/api/partner/login/',
            {'mobile': '9800000093', 'password': 'newpass1'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.data)

    def test_unknown_mobile_does_not_get_an_otp(self):
        res = self.api.post('/api/partner/password/otp/', {'mobile': '9800000099'}, format='json')
        self.assertEqual(res.status_code, 404, res.data)
