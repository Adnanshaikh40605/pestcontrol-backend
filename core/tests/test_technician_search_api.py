"""Technician list search by name / mobile (q and search params)."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Technician


class TechnicianSearchApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tech_search_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

        self.nagraj = Technician.objects.create(
            name='NAGRAJ',
            mobile='9353343071',
            is_active=True,
        )
        self.shivam = Technician.objects.create(
            name='SHIVAM DUEBY',
            mobile='9167065176',
            alternative_mobile='9876543210',
            is_active=True,
        )
        self.other = Technician.objects.create(
            name='ALEX WELSON FRANCIS',
            mobile='9000000001',
            is_active=True,
        )

    def _ids(self, res):
        self.assertEqual(res.status_code, 200, getattr(res, 'data', res.content))
        rows = res.data.get('results', res.data)
        return [row['id'] for row in rows]

    def test_search_param_filters_by_name(self):
        res = self.api.get('/api/v1/technicians/', {'search': 'nagraj'})
        ids = self._ids(res)
        self.assertIn(self.nagraj.id, ids)
        self.assertNotIn(self.shivam.id, ids)
        self.assertNotIn(self.other.id, ids)

    def test_q_param_filters_by_name(self):
        res = self.api.get('/api/v1/technicians/', {'q': 'SHIVAM'})
        ids = self._ids(res)
        self.assertEqual(ids, [self.shivam.id])

    def test_search_by_mobile_digits(self):
        res = self.api.get('/api/v1/technicians/', {'search': '9353343071'})
        ids = self._ids(res)
        self.assertEqual(ids, [self.nagraj.id])

    def test_search_by_mobile_with_country_code_and_spaces(self):
        res = self.api.get('/api/v1/technicians/', {'search': '+91 93533 43071'})
        ids = self._ids(res)
        self.assertEqual(ids, [self.nagraj.id])

    def test_search_by_partial_mobile(self):
        res = self.api.get('/api/v1/technicians/', {'search': '670651'})
        ids = self._ids(res)
        self.assertEqual(ids, [self.shivam.id])

    def test_search_by_alternative_mobile(self):
        res = self.api.get('/api/v1/technicians/', {'search': '9876543210'})
        ids = self._ids(res)
        self.assertEqual(ids, [self.shivam.id])

    def test_empty_search_returns_all(self):
        res = self.api.get('/api/v1/technicians/', {'page_size': 50})
        ids = self._ids(res)
        self.assertIn(self.nagraj.id, ids)
        self.assertIn(self.shivam.id, ids)
        self.assertIn(self.other.id, ids)
