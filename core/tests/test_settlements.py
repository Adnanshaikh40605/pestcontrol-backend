"""
Unit + API tests for Phase 3 technician settlements.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Client, JobCard, Technician, TechnicianSettlement
from core.settlement_engine import (
    approve_settlement,
    build_settlements_for_period,
    mark_settlement_paid,
)
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class SettlementEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='settle_admin', password='pass1234')
        self.client_obj = Client.objects.create(full_name='Settle Client', mobile='9444444444')
        self.tech = Technician.objects.create(
            name='Settle Tech',
            mobile='9555555555',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        self.partner = Partner.objects.create(
            full_name='Settle Tech',
            mobile='9555555555',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
        )
        self.partner.set_password('x')
        self.partner.save()
        self.job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            technician=self.tech,
            partner=self.partner,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.APPROVED,
            visit_payout_amount=Decimal('400.00'),
            technician_pool_amount=Decimal('400.00'),
            status=JobCard.JobStatus.DONE,
            completed_at=timezone.now(),
        )
        self.earning = PartnerEarning.objects.create(
            partner=self.partner,
            job=self.job,
            amount=Decimal('400.00'),
            earning_type=PartnerEarning.EarningType.REVENUE_SHARE,
            is_approved=True,
        )

    def test_build_approve_mark_paid(self):
        today = date.today()
        settlements = build_settlements_for_period(
            period_start=today - timedelta(days=7),
            period_end=today,
            cadence='weekly',
        )
        self.assertEqual(len(settlements), 1)
        s = settlements[0]
        self.assertEqual(s.technician_id, self.tech.id)
        self.assertEqual(s.net_amount, Decimal('400.00'))
        self.assertEqual(s.status, TechnicianSettlement.Status.PENDING_APPROVAL)
        self.assertEqual(s.line_items.count(), 1)
        self.earning.refresh_from_db()
        self.assertIsNotNone(self.earning.settlement_line)

        # Second build should not duplicate
        again = build_settlements_for_period(
            period_start=today - timedelta(days=7),
            period_end=today,
        )
        self.assertEqual(again, [])

        s = approve_settlement(s, user=self.user)
        self.assertEqual(s.status, TechnicianSettlement.Status.APPROVED)
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_status, JobCard.PayoutStatus.APPROVED)

        s = mark_settlement_paid(s, user=self.user)
        self.assertEqual(s.status, TechnicianSettlement.Status.PAID)
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_status, JobCard.PayoutStatus.PAID)

    def test_legacy_earnings_excluded(self):
        self.job.payout_status = JobCard.PayoutStatus.LEGACY_EXEMPT
        self.job.save(update_fields=['payout_status'])
        today = date.today()
        settlements = build_settlements_for_period(
            period_start=today - timedelta(days=7),
            period_end=today,
        )
        self.assertEqual(settlements, [])

    def test_settle_zero_amount_completed_job_moves_to_settled(self):
        """₹0 Done visits must settle and leave Unsettled (not blocked by amount > 0)."""
        from core.models import JobCardTechnicianParticipation
        from core.settlement_engine import settle_jobs_for_technician
        from core.technician_ledger import serialize_ledger_row

        zero_job = JobCard.objects.create(
            client=self.client_obj,
            service_type='Cockroach / Ants',
            price='0',
            total_amount=Decimal('0.00'),
            technician=self.tech,
            partner=self.partner,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.PENDING,
            visit_revenue_amount=Decimal('0.00'),
            technician_pool_amount=Decimal('0.00'),
            company_share_amount=Decimal('0.00'),
            visit_payout_amount=Decimal('0.00'),
            status=JobCard.JobStatus.DONE,
            completed_at=timezone.now(),
            schedule_datetime=timezone.now(),
        )
        JobCardTechnicianParticipation.objects.create(
            jobcard=zero_job,
            technician=self.tech,
            partner=self.partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            is_payout_eligible=True,
            payout_amount_snapshot=Decimal('0.00'),
        )
        before = serialize_ledger_row(zero_job, self.tech)
        self.assertEqual(before['settlement_status'], 'unsettled')
        self.assertEqual(before['technician_share'], '0.00')

        settlement = settle_jobs_for_technician(
            technician=self.tech,
            job_ids=[zero_job.id],
            user=self.user,
        )
        self.assertEqual(settlement.status, TechnicianSettlement.Status.PAID)
        self.assertEqual(settlement.net_amount, Decimal('0.00'))
        self.assertEqual(settlement.line_items.count(), 1)
        self.assertEqual(settlement.line_items.get().amount, Decimal('0.00'))
        self.assertEqual(settlement.line_items.get().job_id, zero_job.id)

        zero_job.refresh_from_db()
        self.assertEqual(zero_job.payout_status, JobCard.PayoutStatus.PAID)
        after = serialize_ledger_row(
            JobCard.objects.prefetch_related(
                'technician_participations__technician',
                'partner_earnings',
                'settlement_line_items__settlement',
                'feedbacks',
            ).get(pk=zero_job.pk),
            self.tech,
        )
        self.assertEqual(after['settlement_status'], 'settled')


@override_settings(REVENUE_MODEL_V2=True)
class SettlementApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='settle_api', password='pass1234')
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_obj = Client.objects.create(full_name='API Settle', mobile='9666666666')
        self.tech = Technician.objects.create(
            name='API Tech',
            mobile='9777777777',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        self.partner = Partner.objects.create(
            full_name='API Tech',
            mobile='9777777777',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
        )
        self.job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='2000',
            total_amount=Decimal('2000.00'),
            technician=self.tech,
            partner=self.partner,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.APPROVED,
            status=JobCard.JobStatus.DONE,
            completed_at=timezone.now(),
        )
        PartnerEarning.objects.create(
            partner=self.partner,
            job=self.job,
            amount=Decimal('800.00'),
            is_approved=True,
        )

    def test_build_list_approve_paid_export(self):
        today = date.today()
        build = self.api.post(
            '/api/v1/settlements/',
            {
                'period_start': (today - timedelta(days=7)).isoformat(),
                'period_end': today.isoformat(),
                'cadence': 'weekly',
            },
            format='json',
        )
        self.assertEqual(build.status_code, 201, build.data)
        self.assertEqual(build.data['count'], 1)
        settlement_id = build.data['results'][0]['id']

        listing = self.api.get('/api/v1/settlements/')
        self.assertEqual(listing.status_code, 200)
        results = listing.data.get('results', listing.data)
        self.assertTrue(any(r['id'] == settlement_id for r in results))

        approve = self.api.post(f'/api/v1/settlements/{settlement_id}/approve/')
        self.assertEqual(approve.status_code, 200, approve.data)
        self.assertEqual(approve.data['status'], 'approved')

        paid = self.api.post(f'/api/v1/settlements/{settlement_id}/mark-paid/')
        self.assertEqual(paid.status_code, 200, paid.data)
        self.assertEqual(paid.data['status'], 'paid')

        export = self.api.get(f'/api/v1/settlements/export/?ids={settlement_id}')
        self.assertEqual(export.status_code, 200)
        self.assertIn(
            'spreadsheetml',
            export['Content-Type'],
        )
        self.assertTrue(export.content[:2] == b'PK')  # xlsx zip header

        report = self.api.get('/api/v1/settlements/revenue-sharing-report/')
        self.assertEqual(report.status_code, 200)
        self.assertTrue(report.content[:2] == b'PK')

    @override_settings(REVENUE_MODEL_V2=False)
    def test_build_blocked_when_flag_off(self):
        today = date.today()
        res = self.api.post(
            '/api/v1/settlements/',
            {
                'period_start': today.isoformat(),
                'period_end': today.isoformat(),
            },
            format='json',
        )
        self.assertEqual(res.status_code, 400)
