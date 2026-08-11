# Tests for booking schedule engine

from datetime import date, datetime, timezone as dt_timezone

from django.test import TestCase

from core.booking_schedule_engine import (
    BookingScheduleEngine,
    build_visit_plans,
    parse_amc_visit_count,
    resolve_recurring_spec,
)
from core.models import Client, JobCard


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

    def test_cockroach_amc_12_monthly(self):
        plans = build_visit_plans('Cockroach / Ants', 'AMC 12 Services', date(2026, 1, 10))
        self.assertEqual(len(plans), 12)
        self.assertEqual(plans[1].visit_date, date(2026, 2, 10))

    def test_mosquito_amc_24_every_fifteen_days(self):
        plans = build_visit_plans('Mosquito', 'AMC 24 Services', date(2026, 6, 1))
        self.assertEqual(len(plans), 24)
        self.assertEqual(plans[0].visit_date, date(2026, 6, 1))
        self.assertEqual(plans[1].visit_date, date(2026, 6, 16))
        self.assertEqual(plans[2].visit_date, date(2026, 7, 1))

    def test_mosquito_amc_48_weekly(self):
        plans = build_visit_plans('Mosquito', 'AMC 48 Services', date(2026, 6, 1))
        self.assertEqual(len(plans), 48)
        self.assertEqual(plans[1].visit_date, date(2026, 6, 8))
        self.assertEqual(plans[4].visit_date, date(2026, 6, 29))

    def test_termite_one_time_single_visit_only(self):
        """Termite is One-Time only — no auto checkup / AMC chain."""
        plans = build_visit_plans('Termite', 'One Time Service', date(2026, 1, 15))
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].visit_type, 'TERMITE TREATMENT')
        self.assertEqual(plans[0].visit_date, date(2026, 1, 15))
        self.assertEqual(plans[0].total_visits, 1)

    def test_bed_bugs_two_services(self):
        plans = build_visit_plans('Bed Bugs', 'One Time Service', date(2026, 1, 15))
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0].visit_type, 'BED BUG SERVICE')
        self.assertEqual(plans[1].visit_date, date(2026, 1, 30))
        self.assertEqual(plans[1].total_visits, 2)

    def test_one_time_single_visit(self):
        plans = build_visit_plans('Mosquito', 'One Time Service', date(2026, 6, 1))
        self.assertEqual(len(plans), 1)
        self.assertEqual(parse_amc_visit_count('One Time Service'), None)

    def test_society_calendar_frequencies(self):
        cases = [
            ('Weekly', 52, date(2026, 7, 8)),
            ('Monthly', 12, date(2026, 8, 1)),
            ('Quarterly', 4, date(2026, 10, 1)),
            ('Half Yearly', 2, date(2027, 1, 1)),
            ('Yearly', 2, date(2027, 7, 1)),
            ('12 Services', 12, date(2026, 8, 1)),
            ('6 Services', 6, date(2026, 9, 1)),
            ('3 Services', 3, date(2026, 11, 1)),
            ('AMC', 12, date(2026, 8, 1)),
        ]
        start = date(2026, 7, 1)
        for plan, expected_count, second_date in cases:
            with self.subTest(plan=plan):
                plans = build_visit_plans(
                    'Rodent',
                    plan,
                    start,
                    contract_months=12,
                )
                self.assertEqual(len(plans), expected_count, plan)
                self.assertEqual(plans[0].visit_date, start)
                if expected_count > 1:
                    self.assertEqual(plans[1].visit_date, second_date, plan)
                self.assertIsNotNone(resolve_recurring_spec(plan))


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

    def test_generate_all_visits_for_mosquito_amc_24(self):
        client = Client.objects.create(full_name='Mosquito AMC', mobile='9876543212', city='Mumbai')
        job = JobCard.objects.create(
            client=client,
            service_type='Mosquito',
            service_items=[
                {'service': 'Mosquito', 'plan': 'AMC 24 Services', 'area': '2 BHK', 'amount': 5000},
            ],
            service_category='AMC',
            schedule_datetime=datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='5000',
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        created = BookingScheduleEngine.generate_all_visits(job)
        self.assertEqual(len(created), 23)
        first_child = created[0]
        self.assertEqual(first_child.visit_type, 'MOSQUITO AMC')
        self.assertEqual(first_child.service_cycle, 2)
        self.assertEqual(first_child.max_cycle, 24)

    def test_society_monthly_generates_upcoming(self):
        client = Client.objects.create(full_name='Society A', mobile='9876543299', city='Mumbai')
        job = JobCard.objects.create(
            client=client,
            service_type='Mosquito Control',
            service_items=[
                {
                    'service': 'Mosquito Control',
                    'plan': 'Monthly',
                    'frequency': 'Monthly',
                    'amount': 10000,
                },
            ],
            service_category='AMC',
            commercial_type='society',
            property_type='Society',
            job_type='Society',
            contract_duration='12',
            society_billing_type='Paid',
            schedule_datetime=datetime(2026, 7, 1, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10am–12pm',
            price='10000',
            reference='Poster',
            client_address='Society address',
            status=JobCard.JobStatus.PENDING,
        )
        created = BookingScheduleEngine.generate_all_visits(job)
        self.assertEqual(len(created), 11)
        self.assertTrue(all(c.status == JobCard.JobStatus.UPCOMING for c in created))
        self.assertTrue(all(c.commercial_type == 'society' for c in created))
        self.assertTrue(
            all(c.booking_category in JobCard.UPCOMING_SERVICE_CATEGORIES for c in created)
        )
