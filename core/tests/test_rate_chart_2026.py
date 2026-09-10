"""Cover the 2026 master rate chart import.

The workbook quotes GST-exclusive basics, which is the opposite of how legacy
rates were stored, so these tests pin the GST basis end to end as well as the
importer's own behaviour.
"""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import PricingRate, PricingRateAuditLog, PricingRegion
from core.pricing.db import get_pricing_data, get_service_types
from core.pricing.gst import rate_gst_payload


def rate(region_slug, service, plan, area):
    return PricingRate.objects.get(
        region__slug=region_slug, service_package=service, plan_type=plan, area_key=area,
    )


class RateChartImportTests(TestCase):
    """The chart is loaded by the command, not by a migration, so import here."""

    @classmethod
    def setUpTestData(cls):
        call_command('import_rate_chart_2026', stdout=StringIO())

    def test_loads_every_rate_into_both_regions(self):
        for slug in ('mumbai', 'lonavala'):
            chart = PricingRate.objects.filter(
                region__slug=slug, notes__startswith='Master Rate Chart 2026',
            )
            self.assertEqual(chart.count(), 312, f'{slug} is missing chart rows')

    def test_stores_the_basic_with_gst_added_on_top(self):
        """Workbook row: Cockroach Standard / 1 BHK = 1250 + 225 = 1475."""
        r = rate('mumbai', 'Cockroach Standard', 'One Time Service', '1 BHK')
        self.assertEqual(r.amount, Decimal('1250.00'))
        self.assertFalse(r.price_includes_gst)
        self.assertEqual(r.gst_percent, Decimal('18.00'))

        breakdown = rate_gst_payload(r)
        self.assertEqual(breakdown['base_amount'], '1250.00')
        self.assertEqual(breakdown['gst_amount'], '225.00')
        self.assertEqual(breakdown['total_with_gst'], '1475.00')

    def test_keeps_the_internal_floor_off_the_customer_price(self):
        r = rate('mumbai', 'Cockroach Standard', 'One Time Service', '1 BHK')
        self.assertEqual(r.floor_amount, Decimal('1100.00'))
        self.assertLess(r.floor_amount, r.amount)

    def test_records_the_billing_basis_where_the_rate_is_not_per_job(self):
        """A per-room hospital rate is meaningless without its unit."""
        r = rate('mumbai', 'General Pest Control', 'One Time Service',
                 'Hospital Room / Ward - Minimum 10 rooms')
        self.assertEqual(r.amount, Decimal('350.00'))
        self.assertEqual(r.billing_basis, 'Per room')

    def test_carries_every_property_segment(self):
        categories = set(
            PricingRate.objects.filter(notes__startswith='Master Rate Chart 2026')
            .values_list('property_category', flat=True)
        )
        self.assertEqual(categories, {
            'residential', 'society', 'hospital', 'hotel',
            'corporate', 'corporate_monthly', 'multi_site', 'addon',
        })

    def test_reprices_a_colliding_legacy_rate_and_logs_it(self):
        """Bed Bugs is the one name shared with the legacy card."""
        r = rate('mumbai', 'Bed Bugs', 'One Time Service', '1 BHK')
        self.assertEqual(r.amount, Decimal('2800.00'))
        self.assertFalse(r.price_includes_gst)
        self.assertEqual(rate_gst_payload(r)['total_with_gst'], '3304.00')

        entry = PricingRateAuditLog.objects.filter(
            rate=r, action='update',
        ).first()
        self.assertIsNotNone(entry, 'a reprice must leave an audit trail')
        self.assertEqual(entry.old_amount, Decimal('2500.00'))
        self.assertEqual(entry.new_amount, Decimal('2800.00'))

    def test_no_amc_row_for_work_the_chart_scopes_separately(self):
        """Bed bug and termite AMC columns just repeat the one-time price."""
        for service in ('Bed Bugs', 'Termite Spot Treatment'):
            plans = get_service_types(region='mumbai').get(service, [])
            self.assertNotIn('AMC 2 Services', plans)
            self.assertNotIn('AMC 1 Service', plans)

    def test_rerunning_changes_nothing(self):
        before = {
            (r.id, r.amount, r.floor_amount, r.price_includes_gst)
            for r in PricingRate.objects.all()
        }
        logs = PricingRateAuditLog.objects.count()

        call_command('import_rate_chart_2026', stdout=StringIO())

        after = {
            (r.id, r.amount, r.floor_amount, r.price_includes_gst)
            for r in PricingRate.objects.all()
        }
        self.assertEqual(before, after)
        self.assertEqual(PricingRateAuditLog.objects.count(), logs,
                         'a no-op run must not write audit noise')

    def test_booking_list_offers_services_not_property_types(self):
        """The Multi-Site sheet keys rows by site type; those are not services."""
        services = get_service_types(region='mumbai')
        for property_type in ('Corporate Branch / Bank', 'Retail Outlet',
                              'Restaurant / Food Outlet', 'Quick-Commerce / Dark Store'):
            self.assertNotIn(property_type, services)

    def test_bed_bug_work_appears_once_not_three_times(self):
        """Three sheets spell the same treatment differently."""
        services = get_service_types(region='mumbai')
        self.assertIn('Bed Bugs', services)
        self.assertNotIn('Bed Bug Package', services)
        self.assertNotIn('Bed Bug Package - 2 services', services)
        # The hotel and hospital rates survive the rename, sized by area.
        self.assertTrue(PricingRate.objects.filter(
            service_package='Bed Bugs', area_key='Hotel - Minimum 3 affected rooms',
        ).exists())

    def test_thermal_fogging_is_one_service(self):
        services = get_service_types(region='mumbai')
        self.assertIn('Mosquito Thermal Fogging', services)
        self.assertNotIn('Thermal Fogging', services)

    def test_chain_rates_are_integrated_ipm_priced_per_outlet_band(self):
        r = rate('mumbai', 'Integrated IPM', '8 Visits/Month',
                 'Quick-Commerce / Dark Store - 26-50 Outlets')
        self.assertEqual(r.amount, Decimal('5100.00'))
        self.assertEqual(r.billing_basis, 'Per outlet/month')
        self.assertEqual(rate_gst_payload(r)['total_with_gst'], '6018.00')

    def test_purge_chart_clears_a_renamed_row(self):
        """Renames change the natural key, so the old row must not linger."""
        stale = PricingRate.objects.create(
            region=PricingRegion.objects.get(slug='mumbai'),
            service_package='Bed Bug Package', plan_type='One Time Service',
            area_key='Somewhere', amount=Decimal('1.00'),
            notes='Master Rate Chart 2026 (v2026-09-07). stale',
        )
        call_command('import_rate_chart_2026', '--region', 'mumbai',
                     '--purge-chart', stdout=StringIO())
        self.assertFalse(PricingRate.objects.filter(pk=stale.pk).exists())
        # and the real rows are back
        self.assertEqual(
            PricingRate.objects.filter(
                region__slug='mumbai', notes__startswith='Master Rate Chart 2026',
            ).count(), 312,
        )

    def test_purge_chart_leaves_rates_it_did_not_import(self):
        legacy = PricingRate.objects.create(
            region=PricingRegion.objects.get(slug='mumbai'),
            service_package='Hand Written', plan_type='One Time Service',
            area_key='2 BHK', amount=Decimal('123.00'), notes='typed in by staff',
        )
        call_command('import_rate_chart_2026', '--region', 'mumbai',
                     '--purge-chart', stdout=StringIO())
        self.assertTrue(PricingRate.objects.filter(pk=legacy.pk).exists())

    def test_per_room_bed_bug_rates_are_reachable_for_non_homes(self):
        from core.pricing.db import get_area_options

        home = get_area_options(region='mumbai', commercial_type='home',
                                selected_services=['Bed Bugs'])
        self.assertIn('2 BHK', home)
        self.assertNotIn('Hotel - Minimum 3 affected rooms', home,
                         'a flat should not be offered a hotel rate')

        hotel = get_area_options(region='mumbai', commercial_type='hotel',
                                 selected_services=['Bed Bugs'])
        self.assertIn('Hotel - Minimum 3 affected rooms', hotel)
        self.assertIn('Hospital Room / Ward - Minimum 3 affected rooms', hotel)

    def test_legacy_cockroach_alias_reaches_hotel_chart_areas(self):
        """Website bookings store 'Cockroach / Ants'; hotel edit must see chart bands."""
        from core.pricing import resolve_service_package
        from core.pricing.db import get_area_options, get_pricing_data

        available = set(get_pricing_data(region='mumbai'))
        self.assertEqual(
            resolve_service_package('Cockroach / Ants', available),
            'Cockroach Standard',
        )

        hotel = get_area_options(
            region='mumbai',
            commercial_type='hotel',
            selected_services=['Cockroach / Ants'],
        )
        self.assertIn('Hotel - 1-10 rooms', hotel)
        self.assertNotIn('1 BHK', hotel, 'commercial hotel must not fall back to BHK')

        home = get_area_options(
            region='mumbai',
            commercial_type='home',
            selected_services=['Cockroach / Ants'],
        )
        self.assertIn('1 BHK', home)
        self.assertNotIn('Hotel - 1-10 rooms', home)

        office = get_area_options(
            region='mumbai',
            commercial_type='office',
            selected_services=['Cockroach / Ants'],
        )
        self.assertEqual(office, [], 'cockroach has no corporate chart bands')

    def test_rate_gst_exposes_property_category_for_crm_filters(self):
        r = rate('mumbai', 'Cockroach Standard', 'One Time Service', 'Hotel - 1-10 rooms')
        payload = rate_gst_payload(r)
        self.assertEqual(payload['property_category'], 'hotel')

    def test_add_ons_stay_out_of_the_booking_matrix(self):
        self.assertTrue(
            PricingRate.objects.filter(region__slug='mumbai', property_category='addon').exists()
        )
        services = get_service_types(region='mumbai')
        for item in ('Rodent cage', 'Extra planned visit', 'Detailed audit report'):
            self.assertNotIn(item, services)

    def test_booking_matrix_quotes_the_gst_inclusive_payable(self):
        table = get_pricing_data(region='mumbai')
        self.assertEqual(table['Cockroach Standard']['One Time Service']['1 BHK'], 1475)
        self.assertEqual(table['General Pest Control']['Monthly - 12 Visits']['Large'], 130272)

    def test_dry_run_writes_nothing(self):
        PricingRate.objects.filter(region__slug='mumbai').delete()
        out = StringIO()
        call_command('import_rate_chart_2026', '--region', 'mumbai', '--dry-run', stdout=out)
        self.assertIn('Dry run', out.getvalue())
        self.assertEqual(PricingRate.objects.filter(region__slug='mumbai').count(), 0)

    def test_skip_existing_leaves_a_hand_edited_rate_alone(self):
        r = rate('mumbai', 'Cockroach Standard', 'One Time Service', '1 BHK')
        r.amount = Decimal('9999.00')
        r.save(update_fields=['amount'])

        call_command('import_rate_chart_2026', '--region', 'mumbai',
                     '--skip-existing', stdout=StringIO())
        r.refresh_from_db()
        self.assertEqual(r.amount, Decimal('9999.00'))

    def test_deactivate_legacy_retires_names_absent_from_the_chart(self):
        legacy = rate('mumbai', 'Cockroach / Ants', 'One Time Service', '1 BHK')
        self.assertTrue(legacy.is_active)

        call_command('import_rate_chart_2026', '--region', 'mumbai',
                     '--deactivate-legacy', stdout=StringIO())

        legacy.refresh_from_db()
        self.assertFalse(legacy.is_active)
        # A name the chart does use stays live.
        self.assertTrue(rate('mumbai', 'Cockroach Standard', 'One Time Service', '1 BHK').is_active)

    def test_unknown_region_is_rejected(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command('import_rate_chart_2026', '--region', 'atlantis', stdout=StringIO())


class FloorAmountExposureTests(TestCase):
    """The workbook is explicit that the floor is not shown to the customer."""

    def test_customer_catalog_does_not_leak_the_internal_floor(self):
        from customer.serializers import CatalogRateSerializer

        region = PricingRegion.objects.create(slug='t', name='T', is_default=False)
        r = PricingRate.objects.create(
            region=region, service_package='S', plan_type='One Time Service',
            area_key='1 BHK', amount=Decimal('1000.00'),
            floor_amount=Decimal('700.00'), price_includes_gst=False,
        )
        data = CatalogRateSerializer(r).data
        self.assertNotIn('floor_amount', data)
        self.assertEqual(data['total_with_gst'], '1180.00')
