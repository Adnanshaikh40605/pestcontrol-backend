"""Cross-check team-reported Technician Ledger scenarios (Aug 2026)."""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase, override_settings

from core.booking_schedule_engine import (
    BookingScheduleEngine,
    sync_plan_flags_from_service_items,
)
from core.models import Client, JobCard, JobCardTechnicianParticipation, Technician
from core.payout_engine import calculate_and_apply_payout, is_amc_economics
from core.technician_ledger import exclude_package_shells, serialize_ledger_row
from partner.models import Partner


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianLedgerCrossCheckTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            full_name='XC Client', mobile='9000000011', city='Pune',
        )
        self.tech = Technician.objects.create(
            name='T1',
            mobile='9111000001',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        self.partner = Partner.objects.create(
            full_name='T1', mobile='9111000001', password='x', core_technician=self.tech,
        )
        self.tech2 = Technician.objects.create(
            name='T2',
            mobile='9111000002',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        self.partner2 = Partner.objects.create(
            full_name='T2', mobile='9111000002', password='x', core_technician=self.tech2,
        )

    def _part(self, job, tech, partner, status='completed'):
        attendance = {
            'completed': JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            'assigned': JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED,
            'checked_in': JobCardTechnicianParticipation.AttendanceStatus.CHECKED_IN,
        }.get(status, status)
        JobCardTechnicianParticipation.objects.update_or_create(
            jobcard=job,
            technician=tech,
            defaults={
                'partner': partner,
                'role': (
                    JobCardTechnicianParticipation.Role.LEAD
                    if tech.id == self.tech.id
                    else JobCardTechnicianParticipation.Role.CREW
                ),
                'attendance_status': attendance,
                'is_payout_eligible': True,
            },
        )

    def test_2122_termite_plus_bedbugs_day1_total_1500(self):
        """Termite 1000 + Bed Bugs half 500 = tech pool 1500 (not combined ÷2 = 1000)."""
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='Termite, Bed Bugs',
            service_items=[
                {'service': 'Termite', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 2500},
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 2500},
            ],
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            price='5000',
            total_amount=5000,
            status=JobCard.JobStatus.DONE,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            technician=self.tech,
            partner=self.partner,
            reference='Poster',
            client_address='x',
        )
        self._part(job, self.tech, self.partner, 'completed')
        JobCard.objects.create(
            client=self.client_obj,
            parent_job=job,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_cycle=2,
            max_cycle=2,
            planned_visit_count=2,
            schedule_datetime=datetime(2026, 8, 15, 10, 0, tzinfo=dt_timezone.utc),
            status=JobCard.JobStatus.UPCOMING,
            is_followup_visit=True,
            price='0',
        )
        BookingScheduleEngine.sync_multi_service_day1_children(job, completing=True)
        calculate_and_apply_payout(job, force=True)
        day1 = list(JobCard.objects.filter(parent_job=job, service_cycle=1))
        for child in day1:
            calculate_and_apply_payout(child, force=True)
        by = {c.source_service: c for c in day1}
        self.assertEqual(Decimal(str(by['Termite'].visit_payout_amount)), Decimal('1000.00'))
        self.assertEqual(Decimal(str(by['Bed Bugs'].visit_payout_amount)), Decimal('500.00'))
        self.assertEqual(
            sum(Decimal(str(c.visit_payout_amount or 0)) for c in day1),
            Decimal('1500.00'),
        )
        self.assertNotIn(job, exclude_package_shells([job] + day1))

    def test_1940_two_tech_assigned_equal_split(self):
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='Termite',
            service_items=[
                {'service': 'Termite', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 6000},
            ],
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            price='6000',
            total_amount=6000,
            status=JobCard.JobStatus.DONE,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            technician=self.tech,
            partner=self.partner,
            reference='Poster',
            client_address='x',
        )
        self._part(job, self.tech, self.partner, 'completed')
        self._part(job, self.tech2, self.partner2, 'assigned')
        calculate_and_apply_payout(job, force=True)
        job.refresh_from_db()
        self.assertEqual(Decimal(str(job.technician_pool_amount)), Decimal('2400.00'))
        snaps = {
            p.technician_id: Decimal(str(p.payout_amount_snapshot or 0))
            for p in job.technician_participations.all()
        }
        self.assertEqual(snaps[self.tech.id], Decimal('1200.00'))
        self.assertEqual(snaps[self.tech2.id], Decimal('1200.00'))

    def test_1925_bed_bugs_first_visit_is_half(self):
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 1900},
            ],
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            price='1900',
            total_amount=1900,
            status=JobCard.JobStatus.DONE,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            technician=self.tech,
            partner=self.partner,
            planned_visit_count=2,
            max_cycle=2,
            service_cycle=1,
            reference='Poster',
            client_address='x',
        )
        self._part(job, self.tech, self.partner, 'completed')
        calculate_and_apply_payout(job, force=True)
        job.refresh_from_db()
        self.assertEqual(Decimal(str(job.visit_revenue_amount)), Decimal('950.00'))
        self.assertEqual(Decimal(str(job.visit_payout_amount)), Decimal('380.00'))
        row = serialize_ledger_row(job, self.tech)
        self.assertEqual(row['booking_type_label'], '2-Service Package')

    def test_1965_edited_onetime_ignores_stale_amc_flags(self):
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='Cockroach / Ants',
            source_service='Cockroach / Ants',
            service_items=[
                {
                    'service': 'Cockroach / Ants',
                    'plan': 'One Time Service',
                    'area': '2 BHK',
                    'amount': 2000,
                },
            ],
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            price='2000',
            total_amount=2000,
            status=JobCard.JobStatus.DONE,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            technician=self.tech,
            partner=self.partner,
            is_amc_main_booking=True,
            service_category=JobCard.ServiceCategory.AMC,
            max_cycle=4,
            planned_visit_count=4,
            reference='Poster',
            client_address='x',
        )
        self._part(job, self.tech, self.partner, 'completed')
        self.assertFalse(is_amc_economics(job))
        changed = sync_plan_flags_from_service_items(job)
        if changed:
            job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))
        result = calculate_and_apply_payout(job, force=True)
        job.refresh_from_db()
        self.assertFalse(result.skipped, result.reason)
        self.assertEqual(Decimal(str(job.visit_payout_amount)), Decimal('800.00'))
        self.assertFalse(job.is_amc_main_booking)

    def test_cockroach_child_not_treated_as_bed_bugs(self):
        """Multi shell items include Bed Bugs — Cockroach day-1 child must stay one-time."""
        from core.payout_engine import is_bed_bug_multi_visit

        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='Cockroach, Bed Bugs',
            service_items=[
                {'service': 'Cockroach', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 1500},
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 2500},
            ],
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            price='4000',
            total_amount=4000,
            status=JobCard.JobStatus.DONE,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            technician=self.tech,
            partner=self.partner,
            reference='Poster',
            client_address='x',
        )
        self._part(job, self.tech, self.partner, 'completed')
        BookingScheduleEngine.sync_multi_service_day1_children(job, completing=True)
        cockroach = JobCard.objects.get(
            parent_job=job, source_service='Cockroach', service_cycle=1,
        )
        self.assertFalse(is_bed_bug_multi_visit(cockroach))
        calculate_and_apply_payout(cockroach, force=True)
        cockroach.refresh_from_db()
        self.assertEqual(Decimal(str(cockroach.visit_payout_amount)), Decimal('600.00'))
