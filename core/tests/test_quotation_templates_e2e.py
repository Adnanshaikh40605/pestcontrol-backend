"""
End-to-end validation for quotation master templates and key user examples.

Run: python3 manage.py test core.tests.test_quotation_templates_e2e -v 2
"""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.models import Quotation


class QuotationTemplatesE2ETest(APITestCase):
    """Validates property+service template behaviour via API payloads."""

    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(username='q_tpl_tester', password='testpass123')
        self.api.force_authenticate(user=self.user)

    def _create_from_template_fields(self, property_type, service_type, scopes, payment_terms):
        payload = {
            'customer_name': 'QA Customer',
            'mobile': '9123456789',
            'contact_person': 'Mr. Test',
            'address': 'Test Address Line 1',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'quotation_type': 'Society',
            'property_type': property_type,
            'template_service_type': service_type,
            'status': 'Draft',
            'total_amount': '3000.00',
            'discount': '0.00',
            'tax_amount': '0.00',
            'grand_total': '3000.00',
            'is_amc': False,
            'visit_count': 1,
            'contract_amount': '0.00',
            'license_number': 'LAID020185',
            'items': [
                {
                    'service_name': service_type,
                    'frequency': 'One Time',
                    'quantity': 1,
                    'rate': '3000.00',
                    'total': '3000.00',
                }
            ],
            'scopes': scopes,
            'payment_terms': payment_terms,
        }
        return self.api.post('/api/v1/quotations/', payload, format='json')

    def _scope_map(self, quotation_id):
        q = Quotation.objects.get(pk=quotation_id)
        return {s.title: s.content for s in q.scopes.all()}

    def test_society_general_pest_control_example(self):
        """User example: Society + General Pest Control."""
        scopes = [
            {
                'title': 'Scope of Work',
                'content': 'Comprehensive gel and spray treatment for common pests in all accessible areas.',
            },
            {
                'title': 'Area Covered',
                'content': 'Flats | Shops | Passages | Staircases | Lift Lobby | Parking | Garden | Drainage | Meter Room | Garbage Area | Security Cabin | Common Areas',
            },
            {
                'title': 'Pest Covered',
                'content': 'Cockroach | Red Ant | Black Ant | Silverfish | Spider | Lizard',
            },
            {
                'title': 'Benefits',
                'content': 'Gel & Spray Treatment | Trained Technicians | Digital Service Report | Odourless Treatment | 100% Service Warranty',
            },
            {
                'title': 'Warranty',
                'content': '100% Service Warranty — free revisit within 30 days if covered pests reappear in treated areas.',
            },
        ]
        payment_terms = [
            {'term': 'Advance', 'description': '50% advance before service commencement.'},
            {'term': 'Balance', 'description': 'Balance on completion of treatment.'},
        ]
        res = self._create_from_template_fields(
            'Society', 'General Pest Control', scopes, payment_terms
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        sm = self._scope_map(res.data['id'])
        self.assertIn('Flats', sm['Area Covered'])
        self.assertIn('Lift Lobby', sm['Area Covered'])
        self.assertIn('Cockroach', sm['Pest Covered'])
        self.assertIn('Gel & Spray Treatment', sm['Benefits'])

    def test_restaurant_general_pest_control_example(self):
        scopes = [
            {'title': 'Scope of Work', 'content': 'Food-safe gel and spray treatment.'},
            {
                'title': 'Area Covered',
                'content': 'Kitchen | Dining Area | Store Room | Counter | Wash Area | Washroom | Food Preparation Area',
            },
            {
                'title': 'Pest Covered',
                'content': 'Cockroach | Red Ant | Black Ant | Silverfish | Spider | Lizard',
            },
            {
                'title': 'Benefits',
                'content': 'Food Safe Treatment | Gel & Spray Treatment | Odourless | Trained Technicians | Digital Report',
            },
            {'title': 'Warranty', 'content': '100% Service Warranty — free revisit within 30 days.'},
        ]
        res = self._create_from_template_fields(
            'Restaurant / Cafe', 'General Pest Control', scopes,
            [{'term': 'Advance', 'description': '50% advance'}],
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sm = self._scope_map(res.data['id'])
        self.assertIn('Kitchen', sm['Area Covered'])
        self.assertIn('Food Safe Treatment', sm['Benefits'])

    def test_hotel_office_villa_area_covered_examples(self):
        cases = [
            (
                'Hotel / Resort',
                'General Pest Control',
                'Rooms | Reception | Lobby | Kitchen | Restaurant | Laundry | Corridors | Store Room | Washrooms',
            ),
            (
                'Office',
                'General Pest Control',
                'Cabins | Workstations | Reception | Pantry | Meeting Room | Store Room | Washroom',
            ),
            (
                'Villa / Bungalow',
                'General Pest Control',
                'Living Room | Bedrooms | Kitchen | Bathrooms | Balcony | Terrace',
            ),
            (
                'Warehouse',
                'Rodent Control',
                'Storage Area | Loading Area | Office | Packing Area | Common Area',
            ),
            (
                'Hospital',
                'General Pest Control',
                'OPD | ICU | Wards | Operation Theatre | Pharmacy | Reception',
            ),
        ]
        for property_type, service_type, area_snippet in cases:
            with self.subTest(property=property_type, service=service_type):
                scopes = [
                    {'title': 'Scope of Work', 'content': 'Test scope'},
                    {'title': 'Area Covered', 'content': area_snippet},
                    {'title': 'Pest Covered', 'content': 'Test pests'},
                    {'title': 'Benefits', 'content': 'Test benefits'},
                    {'title': 'Warranty', 'content': 'Test warranty'},
                ]
                res = self._create_from_template_fields(
                    property_type, service_type, scopes,
                    [{'term': 'Advance', 'description': '50%'}],
                )
                self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
                q = Quotation.objects.get(pk=res.data['id'])
                self.assertEqual(q.property_type, property_type)
                self.assertEqual(q.template_service_type, service_type)
                area = q.scopes.get(title='Area Covered').content
                self.assertIn(area_snippet.split(' | ')[0], area)

    def test_all_property_service_combinations_save(self):
        """11 properties × 4 services = 44 combinations must persist via API."""
        properties = [
            'Residential Flat', 'Villa / Bungalow', 'Society', 'Hotel / Resort',
            'Restaurant / Cafe', 'Office', 'Warehouse', 'Factory', 'Hospital',
            'School / College', 'Shop / Showroom',
        ]
        services = [
            'General Pest Control', 'Rodent Control', 'Mosquito Control', 'Termite Treatment',
        ]
        base_scopes = [
            {'title': 'Scope of Work', 'content': 'Scope'},
            {'title': 'Area Covered', 'content': 'Area A | Area B'},
            {'title': 'Pest Covered', 'content': 'Pest A | Pest B'},
            {'title': 'Benefits', 'content': 'Benefit A'},
            {'title': 'Warranty', 'content': 'Warranty text'},
        ]
        for prop in properties:
            for svc in services:
                with self.subTest(property=prop, service=svc):
                    res = self._create_from_template_fields(
                        prop, svc, base_scopes,
                        [{'term': 'Advance', 'description': '50%'}],
                    )
                    self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
                    q = Quotation.objects.get(pk=res.data['id'])
                    self.assertEqual(q.property_type, prop)
                    self.assertEqual(q.template_service_type, svc)
                    self.assertEqual(q.scopes.count(), 5)

    def test_list_and_preview_fields_roundtrip(self):
        scopes = [
            {'title': 'Scope of Work', 'content': 'Roundtrip scope'},
            {'title': 'Area Covered', 'content': 'Area X'},
            {'title': 'Pest Covered', 'content': 'Pest X'},
            {'title': 'Benefits', 'content': 'Benefit X'},
            {'title': 'Warranty', 'content': 'Warranty X'},
        ]
        create = self._create_from_template_fields(
            'Society', 'Mosquito Control', scopes,
            [{'term': 'Advance', 'description': '50%'}],
        )
        qid = create.data['id']

        listing = self.api.get('/api/v1/quotations/')
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in listing.data.get('results', listing.data)]
        self.assertIn(qid, ids)

        detail = self.api.get(f'/api/v1/quotations/{qid}/')
        self.assertEqual(detail.data['property_type'], 'Society')
        self.assertEqual(detail.data['template_service_type'], 'Mosquito Control')
        self.assertEqual(len(detail.data['scopes']), 5)
        self.assertEqual(len(detail.data['payment_terms']), 1)
