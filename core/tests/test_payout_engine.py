"""
Unit tests for Revenue Model v2 payout engine (40/60).
"""
from decimal import Decimal

from django.test import TestCase, override_settings

from core.models import Client, JobCard, JobCardTechnicianParticipation, Technician
from core.payout_engine import (
    calculate_and_apply_payout,
    split_pool_equally,
)
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class SplitPoolTests(TestCase):
    def test_three_way_split_sums_to_pool(self):
        amounts = split_pool_equally(Decimal('400.00'), 3)
        self.assertEqual(amounts, [Decimal('133.34'), Decimal('133.33'), Decimal('133.33')])
        self.assertEqual(sum(amounts), Decimal('400.00'))

    def test_single_recipient(self):
        amounts = split_pool_equally(Decimal('880.00'), 1)
        self.assertEqual(amounts, [Decimal('880.00')])


@override_settings(REVENUE_MODEL_V2=True)
class PayoutEngineTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            full_name='Test Client',
            mobile='9876543210',
        )

    def _make_partner_tech(self, mobile: str, name: str):
        tech = Technician.objects.create(
            name=name,
            mobile=mobile,
            technician_type=Technician.TechnicianType.PARTNER,
        )
        partner = Partner.objects.create(
            full_name=name,
            mobile=mobile,
            password='x',
            core_technician=tech,
            is_app_approved=True,
        )
        partner.set_password('testpass')
        partner.save()
        return tech, partner

    def _base_job(self, **kwargs):
        defaults = dict(
            client=self.client_obj,
            service_type='General Pest',
            price='2200',
            total_amount=Decimal('2200.00'),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            status=JobCard.JobStatus.DONE,
        )
        defaults.update(kwargs)
        return JobCard.objects.create(**defaults)

    def test_one_time_full_share_to_lead_partner(self):
        tech, partner = self._make_partner_tech('9000000001', 'Lead Tech')
        job = self._base_job(
            technician=tech,
            partner=partner,
            service_category=JobCard.ServiceCategory.ONE_TIME,
            price='1000',
            total_amount=Decimal('1000.00'),
        )
        result = calculate_and_apply_payout(job)
        job.refresh_from_db()
        self.assertFalse(result.skipped)
        self.assertEqual(result.economics, 'one_time')
        self.assertEqual(job.visit_revenue_amount, Decimal('1000.00'))
        self.assertEqual(job.technician_pool_amount, Decimal('400.00'))
        self.assertEqual(job.company_share_amount, Decimal('600.00'))
        self.assertEqual(job.visit_payout_amount, Decimal('400.00'))
        self.assertEqual(job.payout_status, JobCard.PayoutStatus.PENDING)
        earning = PartnerEarning.objects.get(job=job, partner=partner)
        self.assertEqual(earning.amount, Decimal('400.00'))

    def test_amc_per_visit_share(self):
        tech, partner = self._make_partner_tech('9000000002', 'AMC Tech')
        parent = self._base_job(
            technician=tech,
            partner=partner,
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            price='2200',
            total_amount=Decimal('2200.00'),
            max_cycle=3,
            planned_visit_count=3,
        )
        visit = self._base_job(
            technician=tech,
            partner=partner,
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=parent,
            is_followup_visit=True,
            included_in_amc=True,
            price='0',
            total_amount=Decimal('0.00'),
            max_cycle=3,
            service_cycle=2,
        )
        result = calculate_and_apply_payout(visit)
        visit.refresh_from_db()
        self.assertEqual(result.economics, 'amc')
        # 2200/3 = 733.33… quantized; pool = 40%
        self.assertEqual(visit.visit_revenue_amount, Decimal('733.33'))
        self.assertEqual(visit.technician_pool_amount, Decimal('293.33'))
        self.assertEqual(visit.payout_status, JobCard.PayoutStatus.PENDING)
        earning = PartnerEarning.objects.get(job=visit, partner=partner)
        self.assertEqual(earning.amount, Decimal('293.33'))

    def test_amc_1000_three_visits_gives_133_33_per_visit_tech(self):
        """User rule: AMC ₹1000 / 3 visits → tech gets ₹133.33 only for the visit they did."""
        tech_a, partner_a = self._make_partner_tech('9000000011', 'Imtiyaz')
        tech_b, partner_b = self._make_partner_tech('9000000012', 'Mustafa')
        parent = self._base_job(
            technician=tech_a,
            partner=partner_a,
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            price='1000',
            total_amount=Decimal('1000.00'),
            max_cycle=3,
            planned_visit_count=3,
        )
        visit1 = self._base_job(
            technician=tech_a,
            partner=partner_a,
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=parent,
            is_followup_visit=True,
            included_in_amc=True,
            price='0',
            total_amount=Decimal('0.00'),
            max_cycle=3,
            planned_visit_count=3,
            service_cycle=1,
        )
        visit2 = self._base_job(
            technician=tech_b,
            partner=partner_b,
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=parent,
            is_followup_visit=True,
            included_in_amc=True,
            price='0',
            total_amount=Decimal('0.00'),
            max_cycle=3,
            planned_visit_count=3,
            service_cycle=2,
        )
        calculate_and_apply_payout(visit1)
        calculate_and_apply_payout(visit2)
        visit1.refresh_from_db()
        visit2.refresh_from_db()
        # Visit value 1000/3 = 333.33; tech 40% = 133.33; company 60% = 200.00
        self.assertEqual(visit1.visit_revenue_amount, Decimal('333.33'))
        self.assertEqual(visit1.technician_pool_amount, Decimal('133.33'))
        self.assertEqual(visit1.company_share_amount, Decimal('200.00'))
        self.assertEqual(visit1.visit_payout_amount, Decimal('133.33'))
        self.assertEqual(visit2.visit_payout_amount, Decimal('133.33'))
        self.assertEqual(
            PartnerEarning.objects.get(job=visit1, partner=partner_a).amount,
            Decimal('133.33'),
        )
        self.assertEqual(
            PartnerEarning.objects.get(job=visit2, partner=partner_b).amount,
            Decimal('133.33'),
        )
        # Visit 1 tech must NOT also get visit 2 commission
        self.assertFalse(
            PartnerEarning.objects.filter(job=visit2, partner=partner_a).exists()
        )

    def test_partner_without_app_account_still_earns_tech_share(self):
        """CRM desk partner (no Partner app login) must still get Tech 40%."""
        tech = Technician.objects.create(
            name='Desk Partner',
            mobile='9000000013',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        job = self._base_job(
            technician=tech,
            partner=None,
            service_category=JobCard.ServiceCategory.ONE_TIME,
            price='1000',
            total_amount=Decimal('1000.00'),
        )
        result = calculate_and_apply_payout(job)
        job.refresh_from_db()
        self.assertFalse(result.skipped)
        self.assertEqual(job.payout_status, JobCard.PayoutStatus.PENDING)
        self.assertEqual(job.visit_payout_amount, Decimal('400.00'))
        self.assertEqual(job.company_share_amount, Decimal('600.00'))
        part = JobCardTechnicianParticipation.objects.get(jobcard=job, technician=tech)
        self.assertEqual(part.payout_amount_snapshot, Decimal('400.00'))
        self.assertEqual(PartnerEarning.objects.filter(job=job).count(), 0)

    def test_contractual_crew_split_excludes_salaried(self):
        lead, lead_p = self._make_partner_tech('9000000003', 'Lead P')
        crew1, crew1_p = self._make_partner_tech('9000000004', 'Crew1 P')
        crew2, crew2_p = self._make_partner_tech('9000000005', 'Crew2 P')
        salaried = Technician.objects.create(
            name='Salaried',
            mobile='9000000006',
            technician_type=Technician.TechnicianType.SALARIED,
        )
        job = self._base_job(
            technician=lead,
            partner=lead_p,
            job_type=JobCard.JobType.SOCIETY,
            commercial_type=JobCard.CommercialType.SOCIETY,
            price='10000',
            total_amount=Decimal('10000.00'),
            planned_visit_count=10,
            max_cycle=10,
        )
        for tech, partner, role in (
            (lead, lead_p, JobCardTechnicianParticipation.Role.LEAD),
            (crew1, crew1_p, JobCardTechnicianParticipation.Role.CREW),
            (crew2, crew2_p, JobCardTechnicianParticipation.Role.CREW),
            (salaried, None, JobCardTechnicianParticipation.Role.CREW),
        ):
            JobCardTechnicianParticipation.objects.create(
                jobcard=job,
                technician=tech,
                partner=partner,
                role=role,
                attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
                is_payout_eligible=tech.technician_type == Technician.TechnicianType.PARTNER,
            )
        result = calculate_and_apply_payout(job)
        job.refresh_from_db()
        self.assertEqual(result.economics, 'contractual')
        # visit 1000, pool 400, 3 partners → 133.34/133.33/133.33
        self.assertEqual(job.visit_revenue_amount, Decimal('1000.00'))
        self.assertEqual(job.technician_pool_amount, Decimal('400.00'))
        amounts = sorted(
            PartnerEarning.objects.filter(job=job).values_list('amount', flat=True)
        )
        self.assertEqual(amounts, [Decimal('133.33'), Decimal('133.33'), Decimal('133.34')])
        self.assertEqual(PartnerEarning.objects.filter(job=job).count(), 3)
        self.assertFalse(
            JobCardTechnicianParticipation.objects.get(
                jobcard=job, technician=salaried
            ).payout_amount_snapshot
        )

    def test_zero_eligible_partners_holds_payout(self):
        salaried = Technician.objects.create(
            name='Only Salaried',
            mobile='9000000007',
            technician_type=Technician.TechnicianType.SALARIED,
        )
        job = self._base_job(
            technician=salaried,
            job_type=JobCard.JobType.SOCIETY,
            price='5000',
            total_amount=Decimal('5000.00'),
            planned_visit_count=5,
        )
        result = calculate_and_apply_payout(job)
        job.refresh_from_db()
        self.assertEqual(job.payout_status, JobCard.PayoutStatus.HELD)
        self.assertEqual(result.reason, 'no_eligible_partner_attendees')
        self.assertEqual(PartnerEarning.objects.filter(job=job).count(), 0)

    def test_legacy_exempt_skipped(self):
        tech, partner = self._make_partner_tech('9000000008', 'Legacy Tech')
        job = self._base_job(
            technician=tech,
            partner=partner,
            payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT,
        )
        result = calculate_and_apply_payout(job)
        self.assertTrue(result.skipped)
        self.assertEqual(result.reason, 'legacy_exempt')
        self.assertEqual(PartnerEarning.objects.filter(job=job).count(), 0)

    @override_settings(REVENUE_MODEL_V2=False)
    def test_flag_off_skips(self):
        tech, partner = self._make_partner_tech('9000000009', 'Flag Off')
        job = self._base_job(technician=tech, partner=partner)
        result = calculate_and_apply_payout(job)
        self.assertTrue(result.skipped)
        self.assertEqual(result.reason, 'feature_flag_off')
