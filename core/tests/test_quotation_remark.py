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
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.notes, 'Called customer — waiting for approval')
        self.assertTrue(
            QuotationHistory.objects.filter(quotation=self.quotation, action='Remark Added').exists()
        )

        edit = self.client.patch(url, {'remark': 'Approved verbally — convert tomorrow'}, format='json')
        self.assertEqual(edit.status_code, status.HTTP_200_OK)
        self.assertEqual(edit.data['notes'], 'Approved verbally — convert tomorrow')
        self.assertTrue(
            QuotationHistory.objects.filter(quotation=self.quotation, action='Remark Updated').exists()
        )

        clear = self.client.patch(url, {'remark': '   '}, format='json')
        self.assertEqual(clear.status_code, status.HTTP_200_OK)
        self.assertIn(clear.data['notes'], (None, ''))
        self.quotation.refresh_from_db()
        self.assertFalse(bool(self.quotation.notes))
