"""Technician ledger + partner earnings display excl-GST booking amounts."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Client, JobCard, Technician, TechnicianSettlement
from core.pricing.gst import (
    DEFAULT_GST_PERCENT,
    amount_excluding_gst,
    earning_amount_excluding_gst,
    resolve_job_gst_percent,
)
from core.technician_ledger import serialize_ledger_row
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class AmountExcludingGstTests(TestCase):
    def test_strips_default_18_percent(self):
        self.assertEqual(DEFAULT_GST_PERCENT, Decimal('18.00'))
        self.assertEqual(
            amount_excluding_gst(Decimal('1180.00')),
            Decimal('1000.00'),
        )
        self.assertEqual(
            amount_excluding_gst(Decimal('1000.00')),
            Decimal('847.46'),
        )

    def test_custom_rate_from_service_items(self):
        job = JobCard(
            service_items=[{'service': 'Termite', 'gst_percent': '12.00', 'amount': 1120}],
        )
        self.assertEqual(resolve_job_gst_percent(job), Decimal('12.00'))
        self.assertEqual(
            amount_excluding_gst(Decimal('1120.00'), Decimal('12.00')),
            Decimal('1000.00'),
        )

    def test_incentive_not_stripped(self):
        self.assertEqual(
            earning_amount_excluding_gst(
                Decimal('50.00'),
                earning_type='incentive',
            ),
            Decimal('50.00'),
        )
        self.assertEqual(
            earning_amount_excluding_gst(
                Decimal('472.00'),
                earning_type='revenue_share',
            ),
            Decimal('400.00'),
        )

    def test_partner_customer_gst_fields(self):
        from core.pricing.gst import partner_customer_gst_fields

        job = JobCard(
            price='1180',
            total_amount=Decimal('1180.00'),
            service_items=[{'service': 'General', 'gst_percent': '18.00', 'amount': 1180}],
        )
        fields = partner_customer_gst_fields(job)
        self.assertEqual(fields['base_amount'], '1000.00')
        self.assertEqual(fields['gst_amount'], '180.00')
        self.assertEqual(fields['total_amount'], '1180.00')
        self.assertEqual(fields['gst_percent'], '18.00')


@override_settings(REVENUE_MODEL_V2=True)
class LedgerExclGstDisplayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ledger_gst', password='pass')
        self.client_obj = Client.objects.create(
            full_name='GST Customer',
            mobile='9876500011',
        )
        self.tech = Technician.objects.create(
            name='Tech GST',
            mobile='9876500012',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Tech GST',
            mobile='9876500012',
            is_active=True,
            is_app_approved=True,
            core_technician=self.tech,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _done_job(self, *, price='1180', visit='1180', tech='472', company='708'):
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price=price,
            total_amount=Decimal(price),
            technician=self.tech,
            partner=self.partner,
            status=JobCard.JobStatus.DONE,
            partner_status=JobCard.PartnerStatus.COMPLETED,
            completed_at=timezone.now(),
            schedule_datetime=timezone.now(),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.PENDING,
            visit_revenue_amount=Decimal(visit),
            technician_pool_amount=Decimal(tech),
            company_share_amount=Decimal(company),
            visit_payout_amount=Decimal(tech),
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
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

    def test_serialize_ledger_row_shows_excl_gst(self):
        job = self._done_job()
        row = serialize_ledger_row(job, self.tech)
        self.assertEqual(Decimal(row['booking_amount']), Decimal('1000.00'))
        self.assertEqual(Decimal(row['visit_revenue']), Decimal('1000.00'))
        self.assertEqual(Decimal(row['technician_share']), Decimal('400.00'))
        self.assertEqual(Decimal(row['company_share']), Decimal('600.00'))

    def test_ledger_api_returns_excl_gst(self):
        self._done_job()
        res = self.api.get(f'/api/v1/technicians/{self.tech.id}/ledger/')
        self.assertEqual(res.status_code, 200, res.data)
        row = res.data['results'][0]
        self.assertEqual(Decimal(row['visit_revenue']), Decimal('1000.00'))
        self.assertEqual(Decimal(row['technician_share']), Decimal('400.00'))
        self.assertEqual(Decimal(row['company_share']), Decimal('600.00'))

    def test_partner_earnings_history_excl_gst(self):
        self._done_job()
        from partner.utils import generate_partner_tokens

        tokens = generate_partner_tokens(self.partner)
        partner_api = APIClient()
        partner_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = partner_api.get('/api/partner/earnings/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(Decimal(res.data['results'][0]['amount']), Decimal('400.00'))
        self.assertEqual(
            Decimal(res.data['results'][0]['visit_payout_amount']),
            Decimal('400.00'),
        )
        self.assertEqual(Decimal(res.data['total_earnings']), Decimal('400.00'))

    def test_partner_settlement_gross_excl_gst(self):
        self._done_job()
        settlement = TechnicianSettlement.objects.create(
            technician=self.tech,
            partner=self.partner,
            period_start=date.today() - timedelta(days=7),
            period_end=date.today(),
            status=TechnicianSettlement.Status.PAID,
            gross_amount=Decimal('472.00'),
            incentive_amount=Decimal('50.00'),
            deduction_amount=Decimal('0.00'),
            net_amount=Decimal('522.00'),
            paid_at=timezone.now(),
        )
        from partner.utils import generate_partner_tokens

        tokens = generate_partner_tokens(self.partner)
        partner_api = APIClient()
        partner_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = partner_api.get('/api/partner/settlements/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['id'] == settlement.id)
        self.assertEqual(Decimal(row['gross_amount']), Decimal('400.00'))
        self.assertEqual(Decimal(row['incentive_amount']), Decimal('50.00'))
        self.assertEqual(Decimal(row['net_amount']), Decimal('450.00'))
