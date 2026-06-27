"""API test for multi-service quotation (e.g. Bed Bug one-time + Mosquito AMC)."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.models import Quotation


class QuotationMultiServiceTest(APITestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(username='q_multi', password='testpass123')
        self.api.force_authenticate(user=self.user)

    def test_mixed_bedbug_onetime_mosquito_amc(self):
        payload = {
            'customer_name': 'Mixed QA',
            'mobile': '9876512345',
            'contact_person': 'Mr. Mixed',
            'address': 'Society Gate',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'quotation_type': 'Society',
            'property_type': 'Society',
            'template_service_type': 'Bed Bug Treatment, Mosquito Control',
            'status': 'Draft',
            'total_amount': '8500.00',
            'discount': '0.00',
            'tax_amount': '0.00',
            'grand_total': '8500.00',
            'is_amc': True,
            'visit_count': 12,
            'contract_amount': '0.00',
            'license_number': 'LAID020185',
            'items': [
                {
                    'service_name': 'Bed Bug Treatment',
                    'frequency': 'One Time Service',
                    'quantity': 1,
                    'rate': '3500.00',
                    'total': '3500.00',
                    'description': 'One Time Service',
                },
                {
                    'service_name': 'Mosquito Control',
                    'frequency': 'AMC 12 Services — Every Month (Mosquito)',
                    'quantity': 1,
                    'rate': '5000.00',
                    'total': '5000.00',
                    'description': 'AMC 12 Services',
                },
            ],
            'scopes': [
                {'title': 'Area Covered', 'content': 'Flats | Shops | Common Areas'},
                {
                    'title': 'Scope of Work — Bed Bug Treatment',
                    'content': 'Bed bug treatment.\n\nService plan: One Time Service',
                },
                {
                    'title': 'Scope of Work — Mosquito Control',
                    'content': 'Mosquito AMC.\n\nService plan: AMC 12 Services',
                },
            ],
            'payment_terms': [
                {'term': 'Advance', 'description': '50% advance before service commencement.'},
            ],
        }
        res = self.api.post('/api/v1/quotations/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        q = Quotation.objects.get(pk=res.data['id'])
        self.assertEqual(q.property_type, 'Society')
        self.assertIn('Bed Bug Treatment', q.template_service_type)
        self.assertIn('Mosquito Control', q.template_service_type)
        self.assertEqual(q.items.count(), 2)

        detail = self.api.get(f'/api/v1/quotations/{q.id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        names = sorted(i['service_name'] for i in detail.data['items'])
        self.assertEqual(names, ['Bed Bug Treatment', 'Mosquito Control'])

    def test_three_services_persist(self):
        services = 'General Pest Control, Rodent Control, Termite Treatment'
        payload = {
            'customer_name': 'Triple Service',
            'mobile': '9876511111',
            'address': 'Office Park',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'quotation_type': 'Office',
            'property_type': 'Office',
            'template_service_type': services,
            'status': 'Draft',
            'total_amount': '10000.00',
            'discount': '0.00',
            'tax_amount': '0.00',
            'grand_total': '10000.00',
            'is_amc': False,
            'visit_count': 1,
            'contract_amount': '0.00',
            'license_number': 'LAID020185',
            'items': [
                {
                    'service_name': 'General Pest Control',
                    'frequency': 'One Time Service',
                    'quantity': 1,
                    'rate': '3000.00',
                    'total': '3000.00',
                },
                {
                    'service_name': 'Rodent Control',
                    'frequency': 'AMC 3 Services — Every 4 Months (Rodent)',
                    'quantity': 1,
                    'rate': '4000.00',
                    'total': '4000.00',
                },
                {
                    'service_name': 'Termite Treatment',
                    'frequency': 'One Time Treatment — 4 free check-ups over 2 years',
                    'quantity': 1,
                    'rate': '3000.00',
                    'total': '3000.00',
                },
            ],
            'scopes': [{'title': 'Area Covered', 'content': 'Cabins | Workstations'}],
            'payment_terms': [{'term': 'Advance', 'description': '50%'}],
        }
        res = self.api.post('/api/v1/quotations/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(Quotation.objects.get(pk=res.data['id']).items.count(), 3)
