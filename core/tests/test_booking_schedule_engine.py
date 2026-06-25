# Tests for booking schedule engine

from datetime import date

from django.test import TestCase

from core.booking_schedule_engine import (
    build_visit_plans,
    parse_amc_visit_count,
    BookingScheduleEngine,
)
from core.models import Client, JobCard
from datetime import datetime, timezone as dt_timezone


class VisitPlanTests(TestCase):
    def test_cockroach_amc_4_services_interval(self):
        plans = build_visit_plans('Cockroach / Ants', 'AMC 4 Services', date(2026, 7, 15))
        self.assertEqual(len(plans), 4)
        self.assertEqual(plans[0].visit_date, date(2026, 7, 15))
        self.assertEqual(plans[1].visit_date, date(2026, 10, 15))
        self.assertEqual(plans[0].visit_type, 'COCKROACH AMC')

    def test_rodent_amc_12_monthly(self):
        plans = build_visit_plans('Rodent', 'AMC 12 Services', date(2026, 1, 10))
        self.assertEqual(len(plans), 12)
        self.assertEqual(plans[1].visit_date, date(2026, 2, 10))

    def test_termite_five_visits_six_month_gap(self):
        plans = build_visit_plans('Termite', 'One Time Service', date(2026, 1, 15))
        self.assertEqual(len(plans), 5)
        self.assertEqual(plans[0].visit_type, 'TERMITE TREATMENT')
        self.assertEqual(plans[1].visit_type, 'TERMITE CHECK-UP')
        self.assertEqual(plans[4].visit_date, date(2028, 1, 15))

    def test_one_time_single_visit(self):
        plans = build_visit_plans('Mosquito', 'One Time Service', date(2026, 6, 1))
        self.assertEqual(len(plans), 1)
        self.assertEqual(parse_amc_visit_count('One Time Service'), None)


class AutoVisitGenerationTests(TestCase):
    def test_generate_all_visits_for_rodent_amc(self):
        client = Client.objects.create(full_name='Test User', mobile='9876543211', city='Mumbai')
        job = JobCard.objects.create(
            client=client,
            service_type='Rodent',
            service_items=[
                {'service': 'Rodent', 'plan': 'AMC 3 Services', 'area': 'Windows', 'amount': 3000},
            ],
            service_category='AMC',
            schedule_datetime=datetime(2026, 8, 10, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10am–12pm',
            price='3000',
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        created = BookingScheduleEngine.generate_all_visits(job)
        self.assertEqual(len(created), 2)
        self.assertEqual(
            JobCard.objects.filter(parent_job=job, is_auto_generated=True).count(),
            2,
        )
