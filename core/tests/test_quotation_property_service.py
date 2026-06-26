"""Tests for quotation property + service type fields and structured scopes."""
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.models import Quotation, QuotationScope


SOCIETY_GPC_SCOPES = [
    {
        'title': 'Scope of Work',
        'content': 'Comprehensive gel and spray treatment for common pests in all accessible areas.',
    },
    {
        'title': 'Area Covered',
        'content': 'Flats | Shops | Passages | Staircases | Lift Lobby | Parking | Garden',
    },
    {
        'title': 'Pest Covered',
        'content': 'Cockroach | Red Ant | Black Ant | Silverfish | Spider | Lizard',
    },
    {
        'title': 'Benefits',
        'content': 'Gel & Spray Treatment | Trained Technicians | Digital Service Report',
    },
    {
        'title': 'Warranty',
        'content': '100% Service Warranty — free revisit within 30 days if covered pests reappear.',
    },
]


class QuotationPropertyServiceTest(APITestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(username='quotation_tester', password='testpass123')
        self.api.force_authenticate(user=self.user)

    def _payload(self, **overrides):
        data = {
            'customer_name': 'Test Society',
            'mobile': '9876543210',
            'address': 'Test Address',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'quotation_type': 'Society',
            'property_type': 'Society',
            'template_service_type': 'General Pest Control',
            'status': 'Draft',
            'total_amount': '5000.00',
            'discount': '0.00',
            'tax_amount': '0.00',
            'grand_total': '5000.00',
            'is_amc': False,
            'visit_count': 1,
            'contract_amount': '0.00',
            'license_number': 'LAID020185',
            'items': [
                {
                    'service_name': 'General Pest Control',
                    'frequency': 'One Time',
                    'quantity': 1,
                    'rate': '5000.00',
                    'total': '5000.00',
                }
            ],
            'scopes': SOCIETY_GPC_SCOPES,
            'payment_terms': [
                {'term': 'Advance', 'description': '50% advance before service commencement.'},
                {'term': 'Balance', 'description': 'Balance on completion of treatment.'},
            ],
        }
        data.update(overrides)
        return data

    def test_create_quotation_with_property_and_service_type(self):
        response = self.api.post('/api/v1/quotations/', self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        quotation = Quotation.objects.get(pk=response.data['id'])
        self.assertEqual(quotation.property_type, 'Society')
        self.assertEqual(quotation.template_service_type, 'General Pest Control')
        self.assertEqual(quotation.scopes.count(), 5)
        self.assertTrue(
            quotation.scopes.filter(title='Area Covered').exists(),
        )
        self.assertTrue(
            quotation.scopes.filter(title='Pest Covered').exists(),
        )

    def test_retrieve_quotation_includes_property_fields(self):
        create = self.api.post('/api/v1/quotations/', self._payload(), format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)

        detail = self.api.get(f"/api/v1/quotations/{create.data['id']}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['property_type'], 'Society')
        self.assertEqual(detail.data['template_service_type'], 'General Pest Control')
        scope_titles = [s['title'] for s in detail.data['scopes']]
        self.assertIn('Benefits', scope_titles)
        self.assertIn('Warranty', scope_titles)

    def test_update_quotation_property_service_and_scopes(self):
        create = self.api.post('/api/v1/quotations/', self._payload(), format='json')
        qid = create.data['id']

        restaurant_scopes = [
            {
                'title': 'Area Covered',
                'content': 'Kitchen | Dining Area | Store Room | Counter | Wash Area',
            },
            {
                'title': 'Benefits',
                'content': 'Food Safe Treatment | Gel & Spray Treatment | Odourless',
            },
        ] + SOCIETY_GPC_SCOPES[0:1] + SOCIETY_GPC_SCOPES[2:]

        patch = self.api.put(
            f'/api/v1/quotations/{qid}/',
            self._payload(
                property_type='Restaurant / Cafe',
                quotation_type='Restaurant',
                template_service_type='General Pest Control',
                scopes=restaurant_scopes,
            ),
            format='json',
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK, patch.data)

        quotation = Quotation.objects.get(pk=qid)
        self.assertEqual(quotation.property_type, 'Restaurant / Cafe')
        self.assertEqual(quotation.template_service_type, 'General Pest Control')
        area = quotation.scopes.get(title='Area Covered')
        self.assertIn('Kitchen', area.content)

    def test_quotation_scope_titles_persist(self):
        create = self.api.post('/api/v1/quotations/', self._payload(), format='json')
        qid = create.data['id']
        titles = list(
            QuotationScope.objects.filter(quotation_id=qid)
            .order_by('id')
            .values_list('title', flat=True)
        )
        self.assertEqual(
            titles,
            ['Scope of Work', 'Area Covered', 'Pest Covered', 'Benefits', 'Warranty'],
        )
