from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.models import Invoice


class InvoiceCustomerGstApiTests(APITestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(username='invoice_gst', password='testpass123')
        self.api.force_authenticate(user=self.user)

    def _payload(self, **overrides):
        data = {
            'invoice_date': '2026-09-10',
            'billed_by_name': 'Multi Pest Care LLP',
            'billed_by_address': 'Mumbai',
            'customer_name': 'Safal Chhetri',
            'customer_mobile': '9594080841',
            'customer_address': 'Bandra East, Mumbai',
            'customer_gst_number': '27AYTPA2835Q1ZR',
            'booking_code': '',
            'reference': 'Other',
            'tax_amount': '0.00',
            'notes': '',
            'items': [
                {
                    'service': 'General Pest Control',
                    'schedule': '2026-09-10',
                    'technician': 'Ravi',
                    'amount': '2500.00',
                }
            ],
        }
        data.update(overrides)
        return data

    def test_create_persists_customer_gst_number(self):
        response = self.api.post('/api/v1/invoices/', self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['customer_gst_number'], '27AYTPA2835Q1ZR')
        self.assertEqual(response.data['subtotal'], '2500.00')
        self.assertEqual(response.data['grand_total'], '2500.00')
        self.assertTrue(response.data['invoice_no'].startswith('INV-'))

        invoice = Invoice.objects.get(pk=response.data['id'])
        self.assertEqual(invoice.customer_gst_number, '27AYTPA2835Q1ZR')
        self.assertEqual(invoice.items.count(), 1)

    def test_gstin_prefix_stripped_on_save(self):
        response = self.api.post(
            '/api/v1/invoices/',
            self._payload(customer_gst_number='GSTIN 27AYTPA2835Q1ZR'),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['customer_gst_number'], '27AYTPA2835Q1ZR')

    def test_empty_gst_allowed(self):
        response = self.api.post(
            '/api/v1/invoices/',
            self._payload(customer_gst_number=''),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['customer_gst_number'], '')

    def test_update_customer_gst_number(self):
        create = self.api.post('/api/v1/invoices/', self._payload(customer_gst_number=''), format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        invoice_id = create.data['id']

        patch = self.api.patch(
            f'/api/v1/invoices/{invoice_id}/',
            {
                'customer_gst_number': '27AAAAA0000A1Z5',
                'items': [
                    {
                        'service': 'Termite',
                        'schedule': '2026-09-12',
                        'technician': 'Asha',
                        'amount': '6500.00',
                    }
                ],
                'tax_amount': '100.00',
            },
            format='json',
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK, patch.data)
        self.assertEqual(patch.data['customer_gst_number'], '27AAAAA0000A1Z5')
        self.assertEqual(patch.data['subtotal'], '6500.00')
        self.assertEqual(patch.data['grand_total'], '6600.00')
        self.assertEqual(Decimal(patch.data['tax_amount']), Decimal('100.00'))
