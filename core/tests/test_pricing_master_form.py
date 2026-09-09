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


class PricingMasterCityAndPlanFilterTests(TestCase):
    """
    Pricing Master shows one city at a time with no pagination, so the city and
    plan selection has to be applied by the API. Loading every city's rates and
    hiding rows in the browser is what this replaced.
    """

    @classmethod
    def setUpTestData(cls):
        # Slugs the migration does not already seed, so these two cities are
        # isolated from the real Mumbai / Lonavala rate cards.
        cls.mumbai = PricingRegion.objects.create(
            name='Filter Alpha', slug='filter-alpha', is_active=True,
        )
        cls.lonavala = PricingRegion.objects.create(
            name='Filter Beta', slug='filter-beta', is_active=True,
        )
        cls.admin = User.objects.create_superuser(
            username='city-filter-admin', password='x', email='cf@b.com',
        )

        def rate(region, service, plan, area, amount='1000.00', active=True):
            return PricingRate.objects.create(
                region=region,
                service_package=service,
                plan_type=plan,
                area_key=area,
                property_category='residential',
                amount=Decimal(amount),
                gst_percent=Decimal('18.00'),
                price_includes_gst=True,
                is_active=active,
            )

        rate(cls.mumbai, 'Cockroach Standard', 'One Time Service', '1 BHK')
        rate(cls.mumbai, 'Cockroach Premium', 'One Time Service', '1 BHK')
        rate(cls.mumbai, 'Cockroach Standard', 'AMC 3 Services', '1 BHK')
        rate(cls.mumbai, 'Integrated IPM', 'Weekly AMC - 4 Visits/Month', 'Small')
        rate(cls.mumbai, 'Integrated IPM', '4 Visits/Month', 'Small')
        # An inactive rate must stay visible: the status filter was removed, and
        # staff still need to find these to switch them back on.
        rate(cls.mumbai, 'Regular Rodent', 'One Time Service', 'Small', active=False)
        rate(cls.lonavala, 'Bed Bugs', 'One Time Service', 'Single Room')
        rate(cls.lonavala, 'Bed Bugs', 'AMC 3 Services', 'Single Room')

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _rows(self, **params):
        res = self.client.get('/api/v1/pricing-rates/', params)
        self.assertEqual(res.status_code, 200, res.data)
        return res.data['results']

    def test_one_city_returns_only_that_city(self):
        rows = self._rows(region=self.mumbai.id, page_size=500)
        self.assertTrue(rows)
        self.assertEqual({r['region_name'] for r in rows}, {'Filter Alpha'})

    def test_the_other_city_is_independent(self):
        rows = self._rows(region=self.lonavala.id, page_size=500)
        self.assertEqual({r['region_name'] for r in rows}, {'Filter Beta'})

    def test_inactive_rates_are_still_listed(self):
        rows = self._rows(region=self.mumbai.id, page_size=500)
        self.assertIn(False, [r['is_active'] for r in rows])

    def test_plan_family_filter_narrows_to_the_listed_plans(self):
        """One tab covers several stored plan values via plan_type__in."""
        rows = self._rows(
            region=self.mumbai.id,
            plan_type__in='AMC 3 Services,Weekly AMC - 4 Visits/Month',
            page_size=500,
        )
        self.assertEqual(
            {r['plan_type'] for r in rows},
            {'AMC 3 Services', 'Weekly AMC - 4 Visits/Month'},
        )
        self.assertEqual({r['region_name'] for r in rows}, {'Filter Alpha'})

    def test_city_and_plan_apply_together(self):
        rows = self._rows(
            region=self.lonavala.id,
            plan_type__in='One Time Service',
            page_size=500,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['region_name'], 'Filter Beta')
        self.assertEqual(rows[0]['plan_type'], 'One Time Service')

    def test_plan_filter_cannot_leak_another_city(self):
        """Beta has One Time Service rows too — the city must still bind."""
        rows = self._rows(
            region=self.mumbai.id,
            plan_type__in='One Time Service',
            page_size=500,
        )
        self.assertEqual({r['region_name'] for r in rows}, {'Filter Alpha'})

    def test_exact_plan_filter_still_works(self):
        """Pre-existing query param, kept so nothing else breaks."""
        rows = self._rows(region=self.mumbai.id, plan_type='One Time Service', page_size=500)
        self.assertEqual({r['plan_type'] for r in rows}, {'One Time Service'})

    def test_options_scoped_to_a_city_lists_only_its_plans(self):
        """The plan tabs use this, so a city must not be offered a plan it lacks."""
        res = self.client.get('/api/v1/pricing-rates/options/', {'region': self.lonavala.id})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(
            sorted(res.data['plan_types']),
            ['AMC 3 Services', 'One Time Service'],
        )
        self.assertNotIn('4 Visits/Month', res.data['plan_types'])

    def test_unscoped_options_still_list_every_plan(self):
        """The Add/Edit form needs all values so any city can be priced."""
        res = self.client.get('/api/v1/pricing-rates/options/')
        self.assertIn('4 Visits/Month', res.data['plan_types'])
        self.assertIn('Weekly AMC - 4 Visits/Month', res.data['plan_types'])

    def test_a_whole_city_fits_in_one_page_request(self):
        """The UI drops pagination, so page_size has to be able to cover a city."""
        res = self.client.get(
            '/api/v1/pricing-rates/', {'region': self.mumbai.id, 'page_size': 500},
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIsNone(res.data['next'])
        self.assertEqual(len(res.data['results']), res.data['count'])

    def test_exactly_one_city_is_flagged_default(self):
        """The CRM opens the is_default city, so there must be exactly one."""
        res = self.client.get('/api/v1/pricing-regions/')
        self.assertEqual(res.status_code, 200, res.data)
        defaults = [r['name'] for r in res.data['results'] if r['is_default']]
        self.assertEqual(len(defaults), 1, defaults)
        self.assertEqual(defaults, ['Mumbai'])

    def test_service_tabs_are_scoped_to_the_selected_plan(self):
        """A plan must not be offered a service with no rates behind it."""
        res = self.client.get(
            '/api/v1/pricing-rates/options/',
            {'region': self.mumbai.id, 'plan_type__in': 'AMC 3 Services'},
        )
        self.assertEqual(res.status_code, 200, res.data)
        # Only Cockroach Standard has an AMC row in Alpha.
        self.assertEqual(res.data['service_packages'], ['Cockroach Standard'])

    def test_service_tabs_for_a_city_list_every_service_when_no_plan_chosen(self):
        res = self.client.get(
            '/api/v1/pricing-rates/options/', {'region': self.mumbai.id},
        )
        self.assertEqual(
            sorted(res.data['service_packages']),
            ['Cockroach Premium', 'Cockroach Standard', 'Integrated IPM', 'Regular Rodent'],
        )

    def test_standard_and_premium_are_separable_by_service(self):
        """
        The Standard / Premium split lives in the service name, so the service
        tab is what distinguishes them — there is no tier or plan column.
        """
        standard = self._rows(
            region=self.mumbai.id, service_package='Cockroach Standard', page_size=500,
        )
        premium = self._rows(
            region=self.mumbai.id, service_package='Cockroach Premium', page_size=500,
        )
        self.assertEqual({r['service_package'] for r in standard}, {'Cockroach Standard'})
        self.assertEqual({r['service_package'] for r in premium}, {'Cockroach Premium'})
        self.assertEqual(len(standard), 2)
        self.assertEqual(len(premium), 1)

    def test_city_plan_and_service_all_apply_together(self):
        rows = self._rows(
            region=self.mumbai.id,
            plan_type__in='One Time Service',
            service_package='Cockroach Premium',
            page_size=500,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['region_name'], 'Filter Alpha')
        self.assertEqual(rows[0]['plan_type'], 'One Time Service')
        self.assertEqual(rows[0]['service_package'], 'Cockroach Premium')

    def test_service_scoping_does_not_leak_across_cities(self):
        res = self.client.get(
            '/api/v1/pricing-rates/options/', {'region': self.lonavala.id},
        )
        self.assertEqual(res.data['service_packages'], ['Bed Bugs'])
        self.assertNotIn('Cockroach Standard', res.data['service_packages'])
