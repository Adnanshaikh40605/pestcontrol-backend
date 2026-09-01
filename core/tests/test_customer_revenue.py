"""Customer profile revenue split tests (multi-service packages)."""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase

from core.booking_schedule_engine import BookingScheduleEngine
from core.customer_revenue import count_billable_booking_units, iter_revenue_contributions
from core.models import Client, JobCard, Technician
from core.payout_engine import calculate_and_apply_payout, is_contractual_economics


class CustomerRevenueSplitTests(TestCase):
    def setUp(self):
        self.client = Client.objects.create(
            full_name='VAMA EVENTS PVT. LTD',
            mobile='9833401652',
            city='Mumbai',
        )

    def test_multi_service_revenue_splits_amc_and_one_time_lines(self):
        shell = JobCard.objects.create(
            client=self.client,
            service_type='Cockroach / Ants, Termite',
            service_items=[
                {'service': 'Cockroach / Ants', 'plan': 'AMC 3 Services', 'area': 'Commercial', 'amount': 7000},
                {'service': 'Termite', 'plan': 'One Time Service', 'area': 'Commercial', 'amount': 6500},
            ],
            schedule_datetime=datetime(2026, 8, 14, 8, 30, tzinfo=dt_timezone.utc),
            price='13500',
            total_amount=Decimal('13500.00'),
            property_type='Office',
            commercial_type='office',
            status=JobCard.JobStatus.DONE,
            service_category=JobCard.ServiceCategory.AMC,
        )
        contribs = list(iter_revenue_contributions(shell))
        self.assertEqual(len(contribs), 2)
        self.assertEqual(sum(c.amount for c in contribs), Decimal('13500'))
        amc_total = sum(c.amount for c in contribs if c.is_amc)
        one_time_total = sum(c.amount for c in contribs if not c.is_amc)
        self.assertEqual(amc_total, Decimal('7000'))
        self.assertEqual(one_time_total, Decimal('6500'))
        self.assertEqual(count_billable_booking_units(shell), 2)

    def test_termite_child_on_office_uses_full_line_not_amc_divisor(self):
        tech = Technician.objects.create(
            name='Mustafa',
            mobile='9000000099',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        shell = JobCard.objects.create(
            client=self.client,
            service_type='Cockroach / Ants, Termite',
            service_items=[
                {'service': 'Cockroach / Ants', 'plan': 'AMC 3 Services', 'area': 'Commercial', 'amount': 7000},
                {'service': 'Termite', 'plan': 'One Time Service', 'area': 'Commercial', 'amount': 6500},
            ],
            schedule_datetime=datetime(2026, 8, 14, 8, 30, tzinfo=dt_timezone.utc),
            price='13500',
            property_type='Office',
            commercial_type='office',
            max_cycle=3,
            status=JobCard.JobStatus.DONE,
            service_category=JobCard.ServiceCategory.AMC,
            technician=tech,
        )
        BookingScheduleEngine.generate_all_visits(shell)
        termite = JobCard.objects.get(parent_job=shell, source_service='Termite', service_cycle=1)
        termite.price = '6500'
        termite.total_amount = Decimal('6500.00')
        termite.status = JobCard.JobStatus.DONE
        termite.property_type = 'Office'
        termite.commercial_type = 'office'
        termite.save()

        self.assertFalse(is_contractual_economics(termite))
        result = calculate_and_apply_payout(termite, force=True)
        self.assertEqual(result.economics, 'one_time')
        self.assertEqual(result.visit_revenue, Decimal('6500.00'))
        termite.refresh_from_db()
        self.assertEqual(termite.visit_revenue_amount, Decimal('6500.00'))
