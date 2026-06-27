from django.test import TestCase

from core.pricing import build_pricing_config_payload, get_area_options, get_pricing_data, pricing_region_for_city
from core.pricing.lonavala import LONAVALA_PRICING
from core.pricing.mumbai import COMMERCIAL_AREA_KEY, MUMBAI_PRICING
from core.service_rates import compute_service_rate_info


class PricingRegionTests(TestCase):
    def test_mumbai_default_region(self):
        self.assertEqual(pricing_region_for_city('Mumbai'), 'mumbai')
        self.assertEqual(pricing_region_for_city('Pune'), 'mumbai')
        self.assertEqual(pricing_region_for_city(None), 'mumbai')

    def test_lonavala_region(self):
        self.assertEqual(pricing_region_for_city('Lonavala'), 'lonavala')
        self.assertEqual(pricing_region_for_city(' lonavala '), 'lonavala')

    def test_lonavla_typo_resolves_to_lonavala(self):
        """CRM master city is sometimes stored as Lonavla — must not fall back to Mumbai."""
        self.assertEqual(pricing_region_for_city('Lonavla'), 'lonavala')
        payload = build_pricing_config_payload('Lonavla')
        self.assertEqual(payload['region'], 'lonavala')
        self.assertEqual(
            payload['pricing']['Cockroach / Ants']['One Time Service']['4 BHK'],
            2200,
        )


class LonavalaRateCardTests(TestCase):
    def test_general_pest_2_bhk_one_time(self):
        rates = LONAVALA_PRICING['Cockroach / Ants']['One Time Service']
        self.assertEqual(rates['2 BHK'], 1500)

    def test_general_pest_villa_amc(self):
        rates = LONAVALA_PRICING['Cockroach / Ants']['AMC 3 Services']
        self.assertEqual(rates['2,001-4,000 Sq.Ft.'], 10000)

    def test_bed_bug_3_bhk(self):
        self.assertEqual(LONAVALA_PRICING['Bed Bugs']['One Time Service']['3 BHK'], 5000)

    def test_termite_5_bhk(self):
        self.assertEqual(LONAVALA_PRICING['Termite']['One Time Service']['5 BHK'], 7500)

    def test_termite_one_time_treatment_alias_matches_service(self):
        """Booking UI plan label must resolve to the same rates as One Time Service."""
        for region in (MUMBAI_PRICING, LONAVALA_PRICING):
            svc = region['Termite']
            self.assertEqual(
                svc['One Time Treatment']['1 BHK'],
                svc['One Time Service']['1 BHK'],
            )

    def test_mosquito_fogging(self):
        rates = LONAVALA_PRICING['Mosquito']['One Time Service']
        self.assertEqual(rates['5,001-10,000 Sq.Ft.'], 4000)

    def test_rodent_sqft(self):
        rates = LONAVALA_PRICING['Rodent']['One Time Service']
        self.assertEqual(rates['15,001-20,000 Sq.Ft.'], 12000)


class MumbaiRatesUnchangedTests(TestCase):
    def test_mumbai_cockroach_2_bhk(self):
        rates = get_pricing_data('Mumbai')['Cockroach / Ants']['One Time Service']
        self.assertEqual(rates['2 BHK'], 1500)

    def test_mumbai_rodent_windows(self):
        rates = get_pricing_data('Mumbai')['Rodent']['One Time Service']
        self.assertEqual(rates['Windows'], 1000)
        self.assertEqual(rates['Society Area'], 0)

    def test_mumbai_data_matches_legacy_module(self):
        self.assertEqual(get_pricing_data('Mumbai'), MUMBAI_PRICING)


class ServiceRateInfoTests(TestCase):
    def test_lonavala_rate_inquiry_breakdown(self):
        info = compute_service_rate_info(
            pest_type='Cockroach / Ants',
            service_frequency='one-time',
            premise_size='3 BHK',
            service_city='Lonavala',
        )
        self.assertEqual(info['total'], 1800)
        self.assertEqual(info['items'][0]['rate'], 1800)

    def test_mumbai_rate_unchanged(self):
        info = compute_service_rate_info(
            pest_type='Cockroach / Ants',
            service_frequency='one-time',
            premise_size='3 BHK',
            service_city='Mumbai',
        )
        self.assertEqual(info['total'], 1800)

    def test_pricing_config_payload_lonavala(self):
        payload = build_pricing_config_payload('Lonavala')
        self.assertEqual(payload['region'], 'lonavala')
        self.assertIn('6 BHK', payload['residential_locations'])
        self.assertIn('Up to 1,000 Sq.Ft.', payload['villa_locations'])

    def test_lonavala_termite_4_bhk_matches_rate_card(self):
        payload = build_pricing_config_payload('Lonavala')
        self.assertEqual(
            payload['pricing']['Termite']['One Time Service']['4 BHK'],
            6500,
        )

    def test_mumbai_termite_4_bhk_differs_from_lonavala(self):
        mumbai = build_pricing_config_payload('Mumbai')
        lonavala = build_pricing_config_payload('Lonavala')
        self.assertEqual(mumbai['pricing']['Termite']['One Time Service']['4 BHK'], 4000)
        self.assertEqual(lonavala['pricing']['Termite']['One Time Service']['4 BHK'], 6500)


class PricingMasterDbTests(TestCase):
    def test_seeded_mumbai_matches_legacy(self):
        from core.models import PricingRate, PricingRegion

        mumbai = PricingRegion.objects.get(slug='mumbai')
        rate = PricingRate.objects.get(
            region=mumbai,
            service_package='Cockroach / Ants',
            plan_type='One Time Service',
            area_key='2 BHK',
        )
        self.assertEqual(int(rate.amount), 1500)

    def test_seeded_lonavala_bed_bugs(self):
        from core.models import PricingRate, PricingRegion

        lonavala = PricingRegion.objects.get(slug='lonavala')
        rate = PricingRate.objects.get(
            region=lonavala,
            service_package='Bed Bugs',
            plan_type='One Time Service',
            area_key='3 BHK',
        )
        self.assertEqual(int(rate.amount), 5000)

    def test_db_source_in_config(self):
        payload = build_pricing_config_payload('Mumbai')
        self.assertEqual(payload.get('source'), 'database')
        self.assertEqual(
            payload['pricing']['Cockroach / Ants']['One Time Service']['2 BHK'],
            1500,
        )


class CommercialAreaOptionTests(TestCase):
    def test_mumbai_pricing_includes_commercial_area(self):
        rates = MUMBAI_PRICING['Cockroach / Ants']['One Time Service']
        self.assertIn(COMMERCIAL_AREA_KEY, rates)
        self.assertEqual(rates[COMMERCIAL_AREA_KEY], 0)

    def test_get_area_options_other_commercial_includes_commercial(self):
        options = get_area_options(
            city='Mumbai',
            commercial_type='other',
            selected_services=['Cockroach / Ants'],
        )
        self.assertIn('1 BHK', options)
        self.assertIn(COMMERCIAL_AREA_KEY, options)

    def test_get_area_options_home_excludes_commercial(self):
        options = get_area_options(
            city='Mumbai',
            commercial_type='home',
            selected_services=['Cockroach / Ants'],
        )
        self.assertNotIn(COMMERCIAL_AREA_KEY, options)

    def test_seeded_commercial_area_rate(self):
        from core.models import PricingRate, PricingRegion
        from core.pricing.seed import ensure_commercial_area_rates

        ensure_commercial_area_rates()
        mumbai = PricingRegion.objects.get(slug='mumbai')
        rate = PricingRate.objects.get(
            region=mumbai,
            service_package='Cockroach / Ants',
            plan_type='One Time Service',
            area_key=COMMERCIAL_AREA_KEY,
        )
        self.assertEqual(int(rate.amount), 0)
        self.assertEqual(rate.property_category, 'commercial')
