"""Ledger uses the configured service base, not a second GST peel."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import (
    Client,
    JobCard,
    PricingRate,
    PricingRegion,
    Technician,
)
from core.pricing.gst import ledger_base_ratio
from core.technician_ledger import serialize_ledger_row
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class ConfiguredBaseLedgerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='base_ledger', password='pass')
        self.client_obj = Client.objects.create(full_name='Rate Customer', mobile='9000001111')
        self.tech = Technician.objects.create(
            name='Rate Tech',
            mobile='9000001112',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Rate Tech',
            mobile='9000001112',
            is_active=True,
            is_app_approved=True,
            core_technician=self.tech,
        )
        self.region, _ = PricingRegion.objects.get_or_create(
            slug='mumbai',
            defaults={'name': 'Mumbai', 'is_default': True, 'is_active': True},
        )
        for package, area, amount in (
            ('Cockroach Standard', '1 BHK', '1250.00'),
            ('Cockroach Standard', '2 BHK', '1600.00'),
            ('Mosquito Cold Fogging', '1 BHK', '900.00'),
        ):
            PricingRate.objects.update_or_create(
                region=self.region,
                service_package=package,
                plan_type='One Time Service',
                area_key=area,
                defaults={
                    'amount': Decimal(amount),
                    'gst_percent': Decimal('18.00'),
                    'price_includes_gst': False,
                    'is_active': True,
                },
            )

    def _done(self, **kwargs):
        price = kwargs.pop('price')
        tech = kwargs.pop('tech')
        company = kwargs.pop('company')
        job = JobCard.objects.create(
            client=self.client_obj,
            technician=self.tech,
            partner=self.partner,
            status=JobCard.JobStatus.DONE,
            partner_status=JobCard.PartnerStatus.COMPLETED,
            completed_at=timezone.now(),
            schedule_datetime=timezone.now(),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.PENDING,
            price=price,
            total_amount=Decimal(price),
            visit_revenue_amount=Decimal(kwargs.pop('visit', price)),
            technician_pool_amount=Decimal(tech),
            company_share_amount=Decimal(company),
            visit_payout_amount=Decimal(tech),
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
            city='Mumbai',
            **kwargs,
        )
        from core.models import JobCardTechnicianParticipation

        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=self.tech,
            partner=self.partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            payout_amount_snapshot=Decimal(tech),
            share_percent_snapshot=Decimal('100.00'),
            is_payout_eligible=True,
        )
        PartnerEarning.objects.create(
            partner=self.partner,
            job=job,
            amount=Decimal(tech),
            is_approved=True,
            earning_type=PartnerEarning.EarningType.REVENUE_SHARE,
        )
        return job

    def test_cockroach_1bhk_uses_chart_base_not_inclusive_total(self):
        """#3330 shape: stored 1470 is the customer total; chart base is 1250."""
        job = self._done(
            price='1470.00',
            tech='588.00',
            company='882.00',
            service_type='Cockroach / Ants',
            bhk_size='1 BHK',
            gst_paid=True,
            service_items=[{
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
                'area': '1 BHK',
                'amount': 1470.0,
                'base_amount': 1470.0,
                'discount': 0,
            }],
        )
        row = serialize_ledger_row(job, self.tech)
        self.assertEqual(Decimal(row['booking_amount']), Decimal('1250.00'))
        self.assertEqual(Decimal(row['visit_revenue']), Decimal('1250.00'))
        self.assertEqual(Decimal(row['technician_share']), Decimal('500.00'))
        self.assertEqual(Decimal(row['company_share']), Decimal('750.00'))

    def test_2bhk_stored_base_is_not_stripped_again(self):
        """#3257 shape: 1600 is already the 2 BHK base, not a GST-inclusive total."""
        job = self._done(
            price='1600.00',
            tech='640.00',
            company='960.00',
            service_type='Cockroach / Ants',
            bhk_size='2 BHK',
            payment_mode=JobCard.PaymentMode.CASH,
            service_items=[{
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'amount': 1600.0,
                'base_amount': 1600.0,
                'discount': 0,
            }],
        )
        row = serialize_ledger_row(job, self.tech)
        self.assertEqual(Decimal(row['booking_amount']), Decimal('1600.00'))
        self.assertEqual(Decimal(row['technician_share']), Decimal('640.00'))
        self.assertEqual(Decimal(row['company_share']), Decimal('960.00'))
        self.assertNotEqual(Decimal(row['booking_amount']), Decimal('1355.93'))

    def test_another_service_uses_its_own_chart_base(self):
        job = self._done(
            price='900.00',
            tech='360.00',
            company='540.00',
            service_type='Mosquito Cold Fogging',
            bhk_size='1 BHK',
            service_items=[{
                'service': 'Mosquito Cold Fogging',
                'plan': 'One Time Service',
                'area': '1 BHK',
                'amount': 900.0,
                'base_amount': 900.0,
                'discount': 0,
            }],
        )
        row = serialize_ledger_row(job, self.tech)
        self.assertEqual(Decimal(row['booking_amount']), Decimal('900.00'))
        self.assertEqual(Decimal(row['technician_share']), Decimal('360.00'))
        self.assertNotEqual(Decimal(row['booking_amount']), Decimal('1250.00'))

    def test_discount_baked_into_stored_base_is_kept(self):
        job = self._done(
            price='1100.00',
            tech='440.00',
            company='660.00',
            service_type='Cockroach Standard',
            bhk_size='1 BHK',
            service_items=[{
                'service': 'Cockroach Standard',
                'plan': 'One Time Service',
                'area': '1 BHK',
                'amount': 1100.0,
                'base_amount': 1100.0,
                'discount': 150.0,
            }],
        )
        self.assertEqual(ledger_base_ratio(job, Decimal('1100.00')), Decimal('1'))
        row = serialize_ledger_row(job, self.tech)
        self.assertEqual(Decimal(row['booking_amount']), Decimal('1100.00'))
        self.assertEqual(Decimal(row['technician_share']), Decimal('440.00'))

    def test_online_vs_cash_does_not_change_base(self):
        cash = self._done(
            price='1600.00',
            tech='640.00',
            company='960.00',
            payment_mode=JobCard.PaymentMode.CASH,
            service_type='Cockroach Standard',
            bhk_size='2 BHK',
            service_items=[{
                'service': 'Cockroach Standard',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 1600.0,
                'amount': 1600.0,
            }],
        )
        online = self._done(
            price='1600.00',
            tech='640.00',
            company='960.00',
            payment_mode=JobCard.PaymentMode.ONLINE,
            service_type='Cockroach Standard',
            bhk_size='2 BHK',
            service_items=[{
                'service': 'Cockroach Standard',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 1600.0,
                'amount': 1888.0,
            }],
        )
        cash_row = serialize_ledger_row(cash, self.tech)
        online_row = serialize_ledger_row(online, self.tech)
        self.assertEqual(cash_row['booking_amount'], online_row['booking_amount'])
        self.assertEqual(Decimal(online_row['booking_amount']), Decimal('1600.00'))
