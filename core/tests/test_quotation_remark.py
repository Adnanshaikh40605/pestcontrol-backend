from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Quotation, QuotationHistory, QuotationItem


class QuotationRemarkApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='quot_remark_admin',
            password='pass12345',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.user)
        self.quotation = Quotation.objects.create(
            customer_name='Remark Test Co',
            mobile='9876543210',
            address='Test Address',
            city='Mumbai',
            quotation_type=Quotation.QuotationType.COMMERCIAL,
            status=Quotation.QuotationStatus.DRAFT,
            grand_total=1000,
            created_by=self.user,
        )
        QuotationItem.objects.create(
            quotation=self.quotation,
            service_name='Cockroach / Ants',
            frequency='One Time',
            quantity=1,
            rate=1000,
            total=1000,
        )

    def test_add_and_edit_quotation_remark(self):
        url = f'/api/v1/quotations/{self.quotation.id}/remark/'

        add = self.client.patch(url, {'remark': 'Called customer — waiting for approval'}, format='json')
        self.assertEqual(add.status_code, status.HTTP_200_OK)
        self.assertEqual(add.data['notes'], 'Called customer — waiting for approval')
        self.assertTrue(add.data.get('last_remark_at'))
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.notes, 'Called customer — waiting for approval')
        self.assertTrue(
            QuotationHistory.objects.filter(quotation=self.quotation, action='Remark Added').exists()
        )

        edit = self.client.patch(url, {'remark': 'Approved verbally — convert tomorrow'}, format='json')
        self.assertEqual(edit.status_code, status.HTTP_200_OK)
        self.assertEqual(edit.data['notes'], 'Approved verbally — convert tomorrow')
        self.assertTrue(edit.data.get('last_remark_at'))
        self.assertTrue(
            QuotationHistory.objects.filter(quotation=self.quotation, action='Remark Updated').exists()
        )

        clear = self.client.patch(url, {'remark': '   '}, format='json')
        self.assertEqual(clear.status_code, status.HTTP_200_OK)
        self.assertIn(clear.data['notes'], (None, ''))
        self.assertIsNone(clear.data.get('last_remark_at'))
        self.quotation.refresh_from_db()
        self.assertFalse(bool(self.quotation.notes))

    def test_list_exposes_last_remark_at(self):
        empty = self.client.get('/api/v1/quotations/')
        self.assertEqual(empty.status_code, status.HTTP_200_OK)
        row = next(r for r in empty.data['results'] if r['id'] == self.quotation.id)
        self.assertIsNone(row.get('last_remark_at'))

        self.client.patch(
            f'/api/v1/quotations/{self.quotation.id}/remark/',
            {'remark': 'Follow up Monday'},
            format='json',
        )
        listed = self.client.get('/api/v1/quotations/')
        row = next(r for r in listed.data['results'] if r['id'] == self.quotation.id)
        self.assertTrue(row.get('last_remark_at'))
        self.assertIn('+05:30', row['last_remark_at'])

    def test_quotation_stats_endpoint(self):
        res = self.client.get('/api/v1/quotations/stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total'], 1)
        self.assertIn('pending', res.data)
        self.assertIn('approved', res.data)
        self.assertIn('converted', res.data)
        self.assertIn('revenue', res.data)
