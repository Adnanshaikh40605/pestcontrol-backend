"""CRM can replace a forgotten Partner app password from the technician page."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import ActivityLog, Technician
from core.roles import ROLE_BLOG_USER, ensure_user_profile
from partner.models import Partner


class TechnicianForgotPasswordTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            username='pwadmin', email='pw@x.com', password='adminpass1'
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.staff)
        self.tech = Technician.objects.create(name='Ravi Patil', mobile='9611100001')
        self.partner = Partner(
            full_name='Ravi Patil',
            mobile='9611100001',
            role=Partner.Role.TECHNICIAN,
            is_active=True,
            is_app_approved=True,
            core_technician=self.tech,
        )
        self.partner.set_password('oldpass1')
        self.partner.save()

    def _reset(self, tech_id, password, client=None):
        api = client or self.api
        return api.post(
            f'/api/technicians/{tech_id}/reset-password/',
            {'password': password},
            format='json',
        )

    def test_new_password_signs_into_the_partner_app(self):
        response = self._reset(self.tech.id, 'NewPass99')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('NewPass99', response.content.decode())
        self.partner.refresh_from_db()
        self.assertTrue(self.partner.check_password('NewPass99'))
        self.assertFalse(self.partner.check_password('oldpass1'))

        public = APIClient()
        old_login = public.post(
            '/api/partner/login/',
            {'mobile': '9611100001', 'password': 'oldpass1'},
            format='json',
        )
        self.assertEqual(old_login.status_code, 401)
        new_login = public.post(
            '/api/partner/login/',
            {'mobile': '9611100001', 'password': 'NewPass99'},
            format='json',
        )
        self.assertEqual(new_login.status_code, 200)
        self.assertIn('access', new_login.data)

        note = ActivityLog.objects.filter(action='Reset technician password').latest('created_at')
        self.assertNotIn('NewPass99', note.details or '')
        self.assertIn('Ravi Patil', note.details or '')

    def test_staff_login_with_the_same_mobile_gets_the_same_password(self):
        app_user = User.objects.create_user(username='9611100001', password='oldpass1')
        response = self._reset(self.tech.id, 'Shared99')
        self.assertEqual(response.status_code, 200)
        app_user.refresh_from_db()
        self.assertTrue(app_user.check_password('Shared99'))
        self.partner.refresh_from_db()
        self.assertTrue(self.partner.check_password('Shared99'))

    def test_short_or_blank_password_is_rejected_and_the_old_one_still_works(self):
        for bad in ('', '      ', '12345', 123456):
            with self.subTest(bad=bad):
                response = self._reset(self.tech.id, bad)
                self.assertEqual(response.status_code, 400)
        self.partner.refresh_from_db()
        self.assertTrue(self.partner.check_password('oldpass1'))

    def test_technician_without_an_app_login_is_rejected(self):
        plain = Technician.objects.create(name='Desk Only', mobile='9611100002')
        response = self._reset(plain.id, 'NewPass99')
        self.assertEqual(response.status_code, 400)
        self.assertIn('no Partner app login', response.data['error'])

    def test_unlinked_login_on_the_same_mobile_is_updated_and_linked(self):
        tech = Technician.objects.create(name='Same Mobile', mobile='9611100003')
        partner = Partner(
            full_name='Same Mobile',
            mobile='9611100003',
            role=Partner.Role.TECHNICIAN,
            is_active=True,
            is_app_approved=True,
        )
        partner.set_password('oldpass1')
        partner.save()
        response = self._reset(tech.id, 'Linked99')
        self.assertEqual(response.status_code, 200)
        partner.refresh_from_db()
        self.assertEqual(partner.core_technician_id, tech.id)
        self.assertTrue(partner.check_password('Linked99'))

    def test_another_technicians_login_is_left_alone(self):
        owner = Technician.objects.create(name='Owner', mobile='9611100004')
        other = Technician.objects.create(name='Other', mobile='9611100005')
        partner = Partner(
            full_name='Owner',
            mobile='9611100005',
            role=Partner.Role.TECHNICIAN,
            is_active=True,
            core_technician=owner,
        )
        partner.set_password('ownerpass')
        partner.save()
        response = self._reset(other.id, 'Stolen99')
        self.assertEqual(response.status_code, 400)
        partner.refresh_from_db()
        self.assertTrue(partner.check_password('ownerpass'))
        self.assertEqual(partner.core_technician_id, owner.id)

    def test_anonymous_and_non_crm_users_cannot_reset(self):
        guest = APIClient()
        guest_response = self._reset(self.tech.id, 'NewPass99', guest)
        self.assertIn(guest_response.status_code, (401, 403))
        blog_user = User.objects.create_user(username='blogonly', password='blogonly1')
        ensure_user_profile(blog_user, ROLE_BLOG_USER)
        blog_user = User.objects.get(pk=blog_user.pk)
        client = APIClient()
        client.force_authenticate(user=blog_user)
        self.assertEqual(self._reset(self.tech.id, 'NewPass99', client).status_code, 403)
        self.partner.refresh_from_db()
        self.assertTrue(self.partner.check_password('oldpass1'))
