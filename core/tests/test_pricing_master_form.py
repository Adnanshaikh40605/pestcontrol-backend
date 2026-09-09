"""Pricing Master Add/Edit Rate form: options feed and the two fields it gained.

The form used to hard-code four services and five plan types while the imported
2026 rate chart holds thirty and twelve, so most rows could not be created and
an existing row's plan rendered as the wrong option. It also had no input for
`floor_amount` or `billing_basis`, leaving both invisible to staff.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import PricingRate, PricingRegion


class PricingMasterFormAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = PricingRegion.objects.create(
            name='Testville', slug='testville', is_active=True,
        )
        cls.admin = User.objects.create_superuser(
            username='pricing-admin', password='x', email='a@b.com',
        )
        cls.rate = PricingRate.objects.create(
            region=cls.region,
            service_package='Integrated IPM',
            plan_type='4 Visits/Month',
            area_key='Up to 5,000 Sq.Ft.',
            property_category='hotel',
            amount=Decimal('12000.00'),
            floor_amount=Decimal('9000.00'),
            billing_basis='Per month',
            gst_percent=Decimal('18.00'),
            price_includes_gst=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_options_endpoint_reports_values_actually_in_use(self):
        """The dropdowns are built from this, so anything stored must appear."""
        res = self.client.get('/api/v1/pricing-rates/options/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Integrated IPM', res.data['service_packages'])
        self.assertIn('4 Visits/Month', res.data['plan_types'])
        self.assertIn('Per month', res.data['billing_bases'])

    def test_options_endpoint_labels_area_segments_as_areas_not_services(self):
        """'Fogging' read as a service sitting in the Property category list."""
        res = self.client.get('/api/v1/pricing-rates/options/')
        labels = {c['value']: c['label'] for c in res.data['property_categories']}
        self.assertEqual(labels['fogging'], 'Open / Outdoor Area (Sq.Ft.)')
        self.assertEqual(labels['rodent'], 'Rodent / Reptile Zone (Sq.Ft.)')
        self.assertNotIn('Fogging', labels['fogging'])

    def test_rate_payload_exposes_floor_and_billing_basis(self):
        res = self.client.get(f'/api/v1/pricing-rates/{self.rate.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Decimal(str(res.data['floor_amount'])), Decimal('9000.00'))
        self.assertEqual(res.data['billing_basis'], 'Per month')

    def test_form_can_create_a_rate_with_floor_and_basis(self):
        res = self.client.post('/api/v1/pricing-rates/', {
            'region': self.region.id,
            'service_package': 'Cockroach Premium',
            'plan_type': 'Quarterly - 3 Visits',
            'area_key': '2 BHK',
            'property_category': 'residential',
            'amount': '4000.00',
            'floor_amount': '3200.00',
            'billing_basis': 'Per visit',
            'gst_percent': '18.00',
            'price_includes_gst': True,
            'is_active': True,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        created = PricingRate.objects.get(pk=res.data['id'])
        self.assertEqual(created.floor_amount, Decimal('3200.00'))
        self.assertEqual(created.billing_basis, 'Per visit')

    def test_floor_above_the_rate_is_rejected(self):
        """Otherwise the quoted price would start below the walk-away price."""
        res = self.client.patch(
            f'/api/v1/pricing-rates/{self.rate.id}/',
            {'floor_amount': '15000.00'},
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('floor_amount', res.data)
        self.rate.refresh_from_db()
        self.assertEqual(self.rate.floor_amount, Decimal('9000.00'))

    def test_floor_can_be_cleared(self):
        res = self.client.patch(
            f'/api/v1/pricing-rates/{self.rate.id}/',
            {'floor_amount': None},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.rate.refresh_from_db()
        self.assertIsNone(self.rate.floor_amount)

    def test_editing_the_amount_leaves_floor_and_basis_intact(self):
        """The form PATCHes; a partial save must not blank untouched columns."""
        res = self.client.patch(
            f'/api/v1/pricing-rates/{self.rate.id}/',
            {'amount': '13000.00'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.rate.refresh_from_db()
        self.assertEqual(self.rate.amount, Decimal('13000.00'))
        self.assertEqual(self.rate.floor_amount, Decimal('9000.00'))
        self.assertEqual(self.rate.billing_basis, 'Per month')
