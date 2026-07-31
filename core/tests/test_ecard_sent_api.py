"""Tests for Pest e-Card WhatsApp sent-check / mark-sent APIs."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import ECardWhatsAppSend


class ECardSentApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='doh_staff',
            password='pass1234',
            first_name='Rahul',
            last_name='Sharma',
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_check_not_sent(self):
        res = self.api.get('/api/v1/e-card/sent-check/', {'mobile': '9372792693'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertFalse(res.data['already_sent'])
        self.assertEqual(res.data['mobile'], '9372792693')

    def test_check_invalid_mobile(self):
        res = self.api.get('/api/v1/e-card/sent-check/', {'mobile': '123'})
        self.assertEqual(res.status_code, 400)

    def test_mark_then_check(self):
        mark = self.api.post(
            '/api/v1/e-card/mark-sent/',
            {
                'mobile': '919372792693',
                'customer_name': 'Adnan 1',
                'source': 'doh_crm',
            },
            format='json',
        )
        self.assertEqual(mark.status_code, 201, mark.data)
        self.assertTrue(mark.data['already_sent'])
        self.assertEqual(mark.data['mobile'], '9372792693')
        self.assertEqual(mark.data['sent_by'], 'Rahul Sharma')
        self.assertTrue(mark.data['created'])

        check = self.api.get('/api/v1/e-card/sent-check/', {'mobile': '9372792693'})
        self.assertEqual(check.status_code, 200, check.data)
        self.assertTrue(check.data['already_sent'])
        self.assertEqual(check.data['sent_by'], 'Rahul Sharma')
        self.assertIn('sent_at', check.data)

        # Second mark is idempotent — original sender kept
        again = self.api.post(
            '/api/v1/e-card/mark-sent/',
            {'mobile': '9372792693', 'sent_by': 'Someone Else', 'source': 'doh_crm'},
            format='json',
        )
        self.assertEqual(again.status_code, 200, again.data)
        self.assertFalse(again.data['created'])
        self.assertEqual(again.data['sent_by'], 'Rahul Sharma')
        self.assertEqual(ECardWhatsAppSend.objects.filter(mobile='9372792693').count(), 1)

    def test_requires_auth(self):
        anon = APIClient()
        res = anon.get('/api/v1/e-card/sent-check/', {'mobile': '9372792693'})
        self.assertIn(res.status_code, (401, 403))
