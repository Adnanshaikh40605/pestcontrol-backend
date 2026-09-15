"""Catalog matching for home website bookings — rodent/fly/other false-match guards."""
from decimal import Decimal

from django.test import TestCase

from core.models import PricingRate, PricingRegion
from customer.catalog_match import (
    is_home_excluded_rate,
    match_rate_for_pest,
    package_token_matches,
    sanitize_home_booking_rate,
)


class CatalogMatchTests(TestCase):
    def setUp(self):
        self.region, _ = PricingRegion.objects.get_or_create(
            slug='catalog-match-region',
            defaults={'name': 'Catalog Match', 'is_default': False, 'is_active': True},
        )
        self.rates = []

        def add(**kwargs):
            defaults = {
                'region': self.region,
                'plan_type': 'One Time Service',
                'is_active': True,
                'gst_percent': Decimal('18.00'),
                'price_includes_gst': False,
            }
            defaults.update(kwargs)
            rate = PricingRate.objects.create(**defaults)
            self.rates.append(rate)
            return rate

        self.integrated = add(
            service_package='Integrated IPM',
            area_key='Large Hospital - 76-150 beds / 30,001-75,000 sq.ft.',
            property_category='hospital',
            amount=Decimal('24000.00'),
        )
        self.fly_catcher = add(
            service_package='Fly catcher servicing',
            area_key='Per unit/month',
            property_category='addon',
            plan_type='Add-On',
            amount=Decimal('750.00'),
        )
        self.society_general = add(
            service_package='General Pest Control',
            area_key='Large',
            property_category='society',
            amount=Decimal('11500.00'),
        )
        self.regular_rodent = add(
            service_package='Regular Rodent',
            area_key='1 BHK',
            property_category='residential',
            amount=Decimal('1300.00'),
        )
        self.cockroach = add(
            service_package='Cockroach Standard',
            area_key='1 BHK',
            property_category='residential',
            amount=Decimal('1250.00'),
        )
        self.kill_rodent = add(
            service_package='Kill-Rodent System',
            area_key='1 BHK',
            property_category='residential',
            amount=Decimal('1650.00'),
        )

    def test_rat_does_not_match_integrated(self):
        self.assertFalse(package_token_matches(['rat'], 'Integrated IPM'))
        self.assertTrue(package_token_matches(['rat'], 'Rodent / Rat Control'))
        self.assertTrue(package_token_matches(['rodent'], 'Regular Rodent'))

    def test_rodent_matches_regular_not_integrated(self):
        rate = match_rate_for_pest(
            self.rates,
            'rodent',
            is_amc=False,
            premise_type='residential',
            premise_size='1 BHK',
            treatment_quality='standard',
        )
        self.assertIsNotNone(rate)
        self.assertEqual(rate.id, self.regular_rodent.id)
        self.assertNotEqual(rate.id, self.integrated.id)

    def test_house_fly_does_not_match_fly_catcher_addon(self):
        rate = match_rate_for_pest(
            self.rates,
            'house-fly',
            is_amc=False,
            premise_type='residential',
            premise_size='1 BHK',
            treatment_quality='standard',
        )
        self.assertIsNone(rate)
        self.assertTrue(is_home_excluded_rate(self.fly_catcher))

    def test_other_general_does_not_match_society_package(self):
        rate = match_rate_for_pest(
            self.rates,
            'other',
            is_amc=False,
            premise_type='residential',
            premise_size='2 BHK',
            treatment_quality='premium',
        )
        self.assertIsNone(rate)
        self.assertTrue(is_home_excluded_rate(self.society_general))

    def test_cockroach_still_matches_standard(self):
        rate = match_rate_for_pest(
            self.rates,
            'cockroach-ants',
            is_amc=False,
            premise_type='residential',
            premise_size='1 BHK',
            treatment_quality='standard',
        )
        self.assertEqual(rate.id, self.cockroach.id)

    def test_sanitize_replaces_integrated_with_regular_rodent(self):
        rematched, pending = sanitize_home_booking_rate(
            self.integrated,
            service_type='Rodent / Rat Control',
            bhk_size='1 BHK',
            booking_type='one_time',
            package_tier='standard',
            property_type='Home / Flat',
            region_id=self.region.id,
        )
        self.assertFalse(pending)
        self.assertEqual(rematched.id, self.regular_rodent.id)

    def test_sanitize_forces_pending_for_fly_catcher(self):
        rematched, pending = sanitize_home_booking_rate(
            self.fly_catcher,
            service_type='Fly Control',
            bhk_size='1 BHK',
            booking_type='one_time',
            package_tier='standard',
            property_type='Home / Flat',
            region_id=self.region.id,
        )
        self.assertTrue(pending)
        self.assertIsNone(rematched)

    def test_sanitize_forces_pending_for_society_general(self):
        rematched, pending = sanitize_home_booking_rate(
            self.society_general,
            service_type='General Pest Control',
            bhk_size='2 BHK',
            booking_type='one_time',
            package_tier='premium',
            property_type='Home / Flat',
            region_id=self.region.id,
        )
        self.assertTrue(pending)
        self.assertIsNone(rematched)
