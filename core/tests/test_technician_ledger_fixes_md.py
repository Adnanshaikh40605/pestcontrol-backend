"""
Cross-check suite for technician_ledger_fixes.md — every booking/share rule.

Maps MD sections A–G + Final Important Logic to executable assertions.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.booking_schedule_engine import build_visit_plans
from core.models import (
    Client,
    JobCard,
    JobCardTechnicianParticipation,
    Technician,
)
from core.payout_engine import calculate_and_apply_payout
from core.settlement_engine import settle_jobs_for_technician
from core.technician_ledger import heal_stuck_payouts, serialize_ledger_row
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class LedgerFixesMdCrossCheckTests(TestCase):
    """End-to-end cross-check of technician_ledger_fixes.md scenarios."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='md_crosscheck',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_obj = Client.objects.create(
            full_name='Heena',
            mobile='8454845141',
        )

    def _partner_tech(self, mobile: str, name: str):
        tech = Technician.objects.create(
            name=name,
            mobile=mobile,
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
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

    def _job(self, **kwargs):
        defaults = dict(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            status=JobCard.JobStatus.DONE,
            schedule_datetime=timezone.now(),
            property_type='Home / Flat',
            created_by=self.user,
        )
        defaults.update(kwargs)
        return JobCard.objects.create(**defaults)

    def _ledger(self, tech, params=None):
        return self.api.get(f'/api/v1/technicians/{tech.id}/ledger/', params or {})

    # ── A1. One-Time → full 40% ──────────────────────────────────────────

    def test_a1_one_time_full_forty_percent(self):
        tech, partner = self._partner_tech('8111000001', 'Akshay')
        job = self._job(
            technician=tech,
            partner=partner,
            service_type='Cockroach Control',
            service_category=JobCard.ServiceCategory.ONE_TIME,
            price='3000',
            total_amount=Decimal('3000.00'),
        )
        calculate_and_apply_payout(job)
        job.refresh_from_db()
        self.assertEqual(job.visit_revenue_amount, Decimal('3000.00'))
        self.assertEqual(job.visit_payout_amount, Decimal('1200.00'))
        row = serialize_ledger_row(job, tech)
        self.assertEqual(Decimal(row['technician_share']), Decimal('1200.00'))
        self.assertEqual(row['settlement_status'], 'unsettled')
        self.assertEqual(row['settlement_status_label'], 'Unsettled')

    # ── A2. AMC ₹3000 / 3 → ₹400 per completed service, per tech ─────────

    def test_a2_amc_per_service_different_technicians(self):
        akshay, p_a = self._partner_tech('8111000002', 'Akshay')
        rahul, p_r = self._partner_tech('8111000003', 'Rahul')
        sameer, p_s = self._partner_tech('8111000004', 'Sameer')

        parent = self._job(
            technician=akshay,
            partner=p_a,
            service_type='Cockroach Control',
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            price='3000',
            total_amount=Decimal('3000.00'),
            max_cycle=3,
            planned_visit_count=3,
            status=JobCard.JobStatus.DONE,
        )
        # MD: Service 1 Akshay, Service 2 Rahul, Service 3 Sameer (upcoming)
        v1 = self._job(
            technician=akshay,
            partner=p_a,
            service_type='Cockroach Control',
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=parent,
            is_followup_visit=True,
            included_in_amc=True,
            price='0',
            total_amount=Decimal('0.00'),
            max_cycle=3,
            planned_visit_count=3,
            service_cycle=1,
            status=JobCard.JobStatus.DONE,
        )
        v2 = self._job(
            technician=rahul,
            partner=p_r,
            service_type='Cockroach Control',
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=parent,
            is_followup_visit=True,
            included_in_amc=True,
            price='0',
            total_amount=Decimal('0.00'),
            max_cycle=3,
            planned_visit_count=3,
            service_cycle=2,
            status=JobCard.JobStatus.DONE,
        )
        v3 = self._job(
            technician=sameer,
            partner=p_s,
            service_type='Cockroach Control',
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=parent,
            is_followup_visit=True,
            included_in_amc=True,
            price='0',
            total_amount=Decimal('0.00'),
            max_cycle=3,
            planned_visit_count=3,
            service_cycle=3,
            status=JobCard.JobStatus.UPCOMING,
        )

        calculate_and_apply_payout(v1)
        calculate_and_apply_payout(v2)
        v1.refresh_from_db()
        v2.refresh_from_db()

        # Per service value ₹1000, tech 40% = ₹400
        self.assertEqual(v1.visit_revenue_amount, Decimal('1000.00'))
        self.assertEqual(v1.visit_payout_amount, Decimal('400.00'))
        self.assertEqual(v2.visit_payout_amount, Decimal('400.00'))

        row_a = serialize_ledger_row(v1, akshay)
        row_r = serialize_ledger_row(v2, rahul)
        row_s = serialize_ledger_row(v3, sameer)

        self.assertEqual(Decimal(row_a['technician_share']), Decimal('400.00'))
        self.assertEqual(row_a['service_number'], 'Service 1 of 3')
        self.assertEqual(row_a['settlement_status'], 'unsettled')

        self.assertEqual(Decimal(row_r['technician_share']), Decimal('400.00'))
        self.assertEqual(row_r['service_number'], 'Service 2 of 3')

        # Upcoming → no share yet
        self.assertEqual(Decimal(row_s['technician_share']), Decimal('0.00'))
        self.assertEqual(row_s['settlement_status'], 'n_a')

        # Cross-tech isolation: Akshay must not earn on Rahul's visit
        self.assertFalse(PartnerEarning.objects.filter(job=v2, partner=p_a).exists())
        self.assertFalse(PartnerEarning.objects.filter(job=v1, partner=p_r).exists())

        # Ledger API: each tech sees only their completed visits' share
        la = self._ledger(akshay)
        self.assertEqual(la.status_code, 200)
        akshay_ids = {r['job_id'] for r in la.data['results']}
        self.assertIn(v1.id, akshay_ids)
        self.assertNotIn(v2.id, akshay_ids)

    # ── A3. Two techs on same service → ₹200 + ₹200 ──────────────────────

    def test_a3_multi_tech_split_same_service(self):
        t1, p1 = self._partner_tech('8111000005', 'Tech One')
        t2, p2 = self._partner_tech('8111000006', 'Tech Two')
        job = self._job(
            technician=t1,
            partner=p1,
            service_type='Mosquito Control',
            service_category=JobCard.ServiceCategory.ONE_TIME,
            price='1000',
            total_amount=Decimal('1000.00'),
        )
        for tech, partner, role in (
            (t1, p1, JobCardTechnicianParticipation.Role.LEAD),
            (t2, p2, JobCardTechnicianParticipation.Role.CREW),
        ):
            JobCardTechnicianParticipation.objects.create(
                jobcard=job,
                technician=tech,
                partner=partner,
                role=role,
                attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
                is_payout_eligible=True,
            )
        calculate_and_apply_payout(job)
        job.refresh_from_db()
        self.assertEqual(job.technician_pool_amount, Decimal('400.00'))
        amounts = sorted(
            PartnerEarning.objects.filter(job=job).values_list('amount', flat=True)
        )
        self.assertEqual(amounts, [Decimal('200.00'), Decimal('200.00')])

        r1 = serialize_ledger_row(job, t1)
        r2 = serialize_ledger_row(job, t2)
        self.assertEqual(Decimal(r1['technician_share']), Decimal('200.00'))
        self.assertEqual(Decimal(r2['technician_share']), Decimal('200.00'))
        self.assertIn('Tech One', r1['assigned_technicians'])
        self.assertIn('Tech Two', r1['assigned_technicians'])

    # ── B. Service-wise schedule rules ───────────────────────────────────

    def test_b_termite_one_time_only(self):
        plans = build_visit_plans('Termite Control', 'One Time Service', date(2026, 3, 1))
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].total_visits, 1)

    def test_b_bed_bugs_two_services(self):
        plans = build_visit_plans('Bed Bugs', 'One Time Service', date(2026, 3, 1))
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0].total_visits, 2)
        self.assertEqual(plans[1].visit_date, date(2026, 3, 16))

    def test_b_cockroach_amc_three_services(self):
        plans = build_visit_plans('Cockroach Control', 'AMC 3 Services', date(2026, 3, 1))
        self.assertEqual(len(plans), 3)

    def test_b_mosquito_one_time_and_amc(self):
        one = build_visit_plans('Mosquito Control', 'One Time Service', date(2026, 3, 1))
        amc = build_visit_plans('Mosquito Control', 'AMC 12 Services', date(2026, 3, 1))
        self.assertEqual(len(one), 1)
        self.assertEqual(len(amc), 12)

    def test_b_rodent_society_amc(self):
        plans = build_visit_plans(
            'Rodent Control', 'Monthly', date(2026, 3, 1), contract_months=12,
        )
        self.assertEqual(len(plans), 12)

    # ── Bed Bugs payout: package÷2 × 40% (F2 / Final) ────────────────────

    def test_f2_bed_bugs_per_service_share_not_full_booking(self):
        tech, partner = self._partner_tech('8111000007', 'BedBug Tech')
        # MD booking 1925 pattern: full package must NOT pay 40% of whole amount
        job = self._job(
            technician=tech,
            partner=partner,
            service_type='Bed Bugs',
            service_category=JobCard.ServiceCategory.ONE_TIME,
            price='5000',
            total_amount=Decimal('5000.00'),
            planned_visit_count=2,
            max_cycle=2,
            service_cycle=1,
        )
        calculate_and_apply_payout(job)
        job.refresh_from_db()
        # Correct: 5000/2 = 2500 × 40% = 1000  (wrong would be 2000)
        self.assertEqual(job.visit_revenue_amount, Decimal('2500.00'))
        self.assertEqual(job.visit_payout_amount, Decimal('1000.00'))
        self.assertNotEqual(job.visit_payout_amount, Decimal('2000.00'))
        row = serialize_ledger_row(job, tech)
        self.assertEqual(Decimal(row['technician_share']), Decimal('1000.00'))
        self.assertEqual(row['service_number'], 'Service 1 of 2')

    # ── F1. Tech share ₹0 heal ───────────────────────────────────────────

    def test_f1_zero_share_healed_on_ledger_load(self):
        tech, partner = self._partner_tech('8111000008', 'Akshay Zero')
        job = self._job(
            technician=tech,
            partner=partner,
            service_type='General Pest',
            price='2500',
            total_amount=Decimal('2500.00'),
            payout_status=JobCard.PayoutStatus.HELD,
            visit_revenue_amount=Decimal('2500.00'),
            technician_pool_amount=Decimal('1000.00'),
            company_share_amount=Decimal('1500.00'),
            visit_payout_amount=Decimal('0.00'),
        )
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=tech,
            partner=partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            is_payout_eligible=True,
            payout_amount_snapshot=Decimal('0.00'),
        )
        healed = heal_stuck_payouts([job])
        self.assertGreaterEqual(healed, 1)
        job.refresh_from_db()
        self.assertGreater(job.visit_payout_amount, Decimal('0.00'))
        row = serialize_ledger_row(job, tech)
        self.assertEqual(Decimal(row['technician_share']), Decimal('1000.00'))

    # ── C/E/F4. Settle selected → Settled, row stays, date set ───────────

    def test_c_settle_keeps_row_sets_settled_and_date(self):
        tech, partner = self._partner_tech('8111000009', 'Settle Tech')
        job = self._job(
            technician=tech,
            partner=partner,
            price='1000',
            total_amount=Decimal('1000.00'),
        )
        calculate_and_apply_payout(job)
        job.refresh_from_db()

        before = serialize_ledger_row(job, tech)
        self.assertEqual(before['settlement_status'], 'unsettled')
        self.assertIsNone(before['settlement_date'])

        settlement = settle_jobs_for_technician(
            technician=tech,
            job_ids=[job.id],
            user=self.user,
        )
        self.assertEqual(settlement.status, 'paid')
        self.assertEqual(settlement.net_amount, Decimal('400.00'))

        job.refresh_from_db()
        after = serialize_ledger_row(job, tech)
        self.assertEqual(after['settlement_status'], 'settled')
        self.assertEqual(after['settlement_status_label'], 'Settled')
        self.assertTrue(after['settlement_date'])
        self.assertEqual(Decimal(after['pending_amount']), Decimal('0.00'))
        # Row still has booking identity — not deleted
        self.assertEqual(after['job_id'], job.id)
        self.assertTrue(JobCard.objects.filter(pk=job.id).exists())

        # Unsettled filter excludes it; Settled filter includes it
        unsettled = self._ledger(tech, {'settlement_status': 'unsettled'})
        settled = self._ledger(tech, {'settlement_status': 'settled'})
        self.assertEqual(unsettled.data['count'], 0)
        self.assertEqual(settled.data['count'], 1)
        # Old settled must not inflate unsettled payable
        self.assertEqual(Decimal(unsettled.data['unsettled_payable']), Decimal('0.00'))

    def test_c_ledger_row_has_required_md_fields(self):
        tech, partner = self._partner_tech('8111000010', 'Field Tech')
        job = self._job(
            technician=tech,
            partner=partner,
            service_type='Rodent Control',
            property_type='Society',
            commercial_type='society',
            price='3000',
            total_amount=Decimal('3000.00'),
            planned_visit_count=3,
            max_cycle=3,
            service_cycle=2,
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
        )
        calculate_and_apply_payout(job)
        job.refresh_from_db()
        row = serialize_ledger_row(job, tech)
        required = [
            'booking_id', 'booking_date', 'customer_name', 'property_type',
            'service_type', 'booking_type_label', 'service_number',
            'booking_amount', 'visit_revenue', 'technician_share_percent',
            'technician_share', 'assigned_technicians', 'status',
            'settlement_status', 'settlement_status_label', 'settlement_date',
        ]
        for key in required:
            self.assertIn(key, row, f'missing ledger field: {key}')
        self.assertEqual(row['customer_name'], 'Heena')
        self.assertEqual(row['property_type'], 'Society')
        self.assertEqual(row['service_number'], 'Service 2 of 3')
        self.assertEqual(row['technician_share_percent'], '40.00')

    # ── F3. Visit Done vs Pay Unsettled (not confusing Pending) ──────────

    def test_f3_done_visit_shows_unsettled_not_pending_label(self):
        tech, partner = self._partner_tech('8111000011', 'Done Tech')
        job = self._job(technician=tech, partner=partner)
        calculate_and_apply_payout(job)
        job.refresh_from_db()
        row = serialize_ledger_row(job, tech)
        self.assertEqual(row['status'], 'Done')
        self.assertTrue(row['is_completed_visit'])
        self.assertEqual(row['settlement_status_label'], 'Unsettled')
        self.assertNotEqual(row['settlement_status_label'], 'Pending')
        self.assertNotEqual(row['payout_status_label'], 'Pending')

    # ── G1. Customer history revenue not doubled ─────────────────────────

    def test_g1_customer_history_revenue_not_double(self):
        tech, partner = self._partner_tech('8111000012', 'Hist Tech')
        # Main AMC ₹3000 + child visit with price mirrored (bug pattern)
        parent = self._job(
            technician=tech,
            partner=partner,
            service_type='Cockroach Control',
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            price='3000',
            total_amount=Decimal('3000.00'),
            max_cycle=3,
            planned_visit_count=3,
            status=JobCard.JobStatus.DONE,
            payment_status=JobCard.PaymentStatus.PAID,
        )
        self._job(
            technician=tech,
            partner=partner,
            service_type='Cockroach Control',
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=parent,
            is_followup_visit=True,
            included_in_amc=True,
            price='3000',  # accidental duplicate amount on child
            total_amount=Decimal('3000.00'),
            max_cycle=3,
            planned_visit_count=3,
            service_cycle=2,
            status=JobCard.JobStatus.DONE,
            payment_status=JobCard.PaymentStatus.PAID,
        )
        res = self.api.get(f'/api/v1/customer-history/{self.client_obj.id}/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(float(res.data['stats']['total_revenue']), 3000.0)

    # ── G2. Termite upcoming not listed / not auto-generated ─────────────

    def test_g2_termite_upcoming_hidden_and_not_auto_generated(self):
        tech, partner = self._partner_tech('8111000013', 'Termite Tech')
        main = self._job(
            technician=tech,
            partner=partner,
            service_type='Termite Control',
            visit_type='TERMITE TREATMENT',
            service_category=JobCard.ServiceCategory.ONE_TIME,
            price='3000',
            total_amount=Decimal('3000.00'),
            status=JobCard.JobStatus.DONE,
            payment_status=JobCard.PaymentStatus.PAID,
            booking_category=JobCard.BookingCategory.NORMAL_BOOKING,
        )
        # Legacy bad data: fake Termite checkup upcoming children
        for i in range(1, 6):
            self._job(
                technician=tech,
                partner=partner,
                service_type='Termite Control',
                visit_type='TERMITE CHECK-UP',
                source_service='Termite Control',
                parent_job=main,
                is_followup_visit=True,
                price='0',
                total_amount=Decimal('0.00'),
                status=JobCard.JobStatus.UPCOMING,
                booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
                service_cycle=i + 1,
                schedule_datetime=timezone.now() + timedelta(days=30 * i),
                next_service_date=timezone.localdate() + timedelta(days=30 * i),
            )

        res = self.api.get(f'/api/v1/customer-history/{self.client_obj.id}/')
        self.assertEqual(res.status_code, 200, res.data)
        upcoming = res.data['upcoming']
        termite_upcoming = [
            u for u in upcoming
            if 'termite' in (u.get('service_type') or '').lower()
            or 'termite' in (u.get('visit_type') or '').lower()
        ]
        self.assertEqual(
            len(termite_upcoming),
            0,
            f'Termite upcoming should be hidden, got {termite_upcoming}',
        )

        # New bookings: schedule engine must not create checkup chain
        plans = build_visit_plans('Termite', 'AMC 5 Services', date(2026, 1, 1))
        self.assertEqual(len(plans), 1)

    # ── Final Important Logic bundle ─────────────────────────────────────

    def test_final_payment_is_per_completed_visit_not_booking(self):
        tech, partner = self._partner_tech('8111000014', 'Final Tech')
        parent = self._job(
            technician=tech,
            partner=partner,
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            price='3000',
            total_amount=Decimal('3000.00'),
            max_cycle=3,
            planned_visit_count=3,
            status=JobCard.JobStatus.DONE,
        )
        # Only 1 of 3 visits completed
        v1 = self._job(
            technician=tech,
            partner=partner,
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
        calculate_and_apply_payout(v1)
        v1.refresh_from_db()
        # Must get one service share (₹400), NOT full booking 40% (₹1200)
        self.assertEqual(v1.visit_payout_amount, Decimal('400.00'))
        self.assertNotEqual(v1.visit_payout_amount, Decimal('1200.00'))
