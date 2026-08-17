# Tests for booking schedule engine

from datetime import date, datetime, timezone as dt_timezone

from django.test import TestCase

from core.booking_schedule_engine import (
    BookingScheduleEngine,
    build_visit_plans,
    heal_all_bed_bug_packages,
    heal_bed_bug_package,
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

    def test_termite_ignores_amc_plan_and_preferred_count(self):
        """Regression: Termite must never become AMC even if plan says AMC 5/12."""
        for plan in ('AMC 5 Services', 'AMC 12 Services', 'AMC', 'Monthly'):
            with self.subTest(plan=plan):
                plans = build_visit_plans(
                    'Termite Control',
                    plan,
                    date(2026, 1, 15),
                    preferred_visit_count=5,
                )
                self.assertEqual(len(plans), 1, plan)
                self.assertEqual(plans[0].total_visits, 1, plan)
                self.assertEqual(plans[0].visit_type, 'TERMITE TREATMENT', plan)

    def test_bed_bugs_two_services(self):
        plans = build_visit_plans('Bed Bugs', 'One Time Service', date(2026, 1, 15))
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0].visit_type, 'BED BUG SERVICE')
        self.assertEqual(plans[1].visit_date, date(2026, 1, 30))
        self.assertEqual(plans[1].total_visits, 2)

    def test_bed_bugs_ignores_amc_plan_stays_two(self):
        """Regression: Bed Bugs max 2 services even if booked as AMC 12."""
        plans = build_visit_plans(
            'Bed Bugs',
            'AMC 12 Services',
            date(2026, 3, 1),
            preferred_visit_count=12,
        )
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0].total_visits, 2)
        self.assertEqual(plans[1].total_visits, 2)
        self.assertTrue(all(p.visit_type == 'BED BUG SERVICE' for p in plans))

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

    def test_termite_amc_payload_creates_zero_children_and_stays_one_time(self):
        """Even if CRM/API sends Termite + AMC plan, generate exactly 0 follow-ups."""
        client = Client.objects.create(full_name='Termite User', mobile='9876543301', city='Pune')
        job = JobCard.objects.create(
            client=client,
            service_type='Termite',
            service_items=[
                {'service': 'Termite', 'plan': 'AMC 5 Services', 'area': '2 BHK', 'amount': 5000},
            ],
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            max_cycle=5,
            planned_visit_count=5,
            schedule_datetime=datetime(2026, 8, 10, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='5000',
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        created = BookingScheduleEngine.generate_all_visits(job)
        job.refresh_from_db()
        self.assertEqual(len(created), 0)
        self.assertEqual(
            JobCard.objects.filter(parent_job=job, is_auto_generated=True).count(),
            0,
        )
        self.assertEqual(job.max_cycle, 1)
        self.assertEqual(job.planned_visit_count, 1)
        self.assertEqual(job.service_category, JobCard.ServiceCategory.ONE_TIME)
        self.assertFalse(job.is_amc_main_booking)

    def test_bed_bugs_creates_exactly_one_followup_not_amc(self):
        client = Client.objects.create(full_name='BedBug User', mobile='9876543302', city='Pune')
        job = JobCard.objects.create(
            client=client,
            service_type='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'AMC 12 Services', 'area': '2 BHK', 'amount': 4000},
            ],
            service_category=JobCard.ServiceCategory.AMC,
            max_cycle=12,
            schedule_datetime=datetime(2026, 8, 10, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='4000',
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        created = BookingScheduleEngine.generate_all_visits(job)
        job.refresh_from_db()
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].service_cycle, 2)
        self.assertEqual(created[0].max_cycle, 2)
        self.assertEqual(created[0].visit_type, 'BED BUG SERVICE')
        self.assertFalse(created[0].included_in_amc)
        self.assertEqual(created[0].service_category, JobCard.ServiceCategory.ONE_TIME)
        self.assertEqual(job.max_cycle, 2)
        self.assertEqual(job.planned_visit_count, 2)
        self.assertEqual(job.service_category, JobCard.ServiceCategory.ONE_TIME)
        self.assertFalse(job.is_amc_main_booking)

    def test_legacy_one_time_bed_bugs_is_healed_to_two_visits(self):
        """Already-created Bed Bugs jobs saved as 1-visit One Time get visit 2."""
        client = Client.objects.create(
            full_name='Legacy BedBug', mobile='9876543303', city='Pune',
        )
        job = JobCard.objects.create(
            client=client,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '1 RK', 'amount': 1900},
            ],
            service_category=JobCard.ServiceCategory.ONE_TIME,
            max_cycle=1,
            planned_visit_count=1,
            service_cycle=1,
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='1900',
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        self.assertEqual(
            JobCard.objects.filter(parent_job=job, service_cycle=2).count(),
            0,
        )
        created = heal_bed_bug_package(job)
        job.refresh_from_db()
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].service_cycle, 2)
        self.assertEqual(created[0].visit_type, 'BED BUG SERVICE')
        self.assertEqual(job.max_cycle, 2)
        self.assertEqual(job.planned_visit_count, 2)
        self.assertTrue(
            JobCard.objects.filter(parent_job=job, service_cycle=2).exists()
        )
        # Idempotent — opening the same booking again must not duplicate visit 2.
        again = heal_bed_bug_package(job)
        self.assertEqual(again, [])
        self.assertEqual(
            JobCard.objects.filter(parent_job=job, service_cycle=2).count(),
            1,
        )

    def test_wrongly_flagged_followup_root_still_gets_second_visit(self):
        client = Client.objects.create(
            full_name='Flagged BedBug', mobile='9876543304', city='Pune',
        )
        job = JobCard.objects.create(
            client=client,
            service_type='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '1 RK', 'amount': 1900},
            ],
            max_cycle=1,
            planned_visit_count=1,
            is_followup_visit=True,
            included_in_amc=True,
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='1900',
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        created = BookingScheduleEngine.generate_all_visits(job)
        job.refresh_from_db()
        self.assertEqual(len(created), 1)
        self.assertFalse(job.is_followup_visit)
        self.assertEqual(job.max_cycle, 2)

    def test_heal_all_backfills_existing_bed_bug_bookings(self):
        client = Client.objects.create(
            full_name='Sweep BedBug', mobile='9876543305', city='Pune',
        )
        JobCard.objects.create(
            client=client,
            service_type='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '1 RK', 'amount': 1900},
            ],
            max_cycle=1,
            planned_visit_count=1,
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='1900',
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        result = heal_all_bed_bug_packages()
        self.assertGreaterEqual(result['healed'], 1)
        self.assertGreaterEqual(result['created_visits'], 1)
        self.assertEqual(
            JobCard.objects.filter(
                client=client, parent_job__isnull=False, service_cycle=2,
            ).count(),
            1,
        )


class MultiServiceSeparateVisitTests(TestCase):
    """Cockroach + Bed Bugs + Mosquito → separate JobCards (not one combined ledger row)."""

    def test_backfill_creates_day1_when_only_followups_exist(self):
        """Legacy multi packages often only had cycle 2+ children — heal day-1 rows."""
        client = Client.objects.create(
            full_name='Legacy Multi', mobile='9876543400', city='Pune',
        )
        job = JobCard.objects.create(
            client=client,
            service_type='Termite, Bed Bugs',
            service_items=[
                {'service': 'Termite', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 2500},
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 2500},
            ],
            schedule_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='5000',
            total_amount=5000,
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.DONE,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
        )
        # Simulate legacy: only Bed Bugs cycle 2 exists (no day-1 rows).
        JobCard.objects.create(
            client=client,
            parent_job=job,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_cycle=2,
            max_cycle=2,
            planned_visit_count=2,
            schedule_datetime=datetime(2026, 8, 15, 10, 0, tzinfo=dt_timezone.utc),
            status=JobCard.JobStatus.UPCOMING,
            is_followup_visit=True,
            is_auto_generated=True,
            price='0',
            total_amount=0,
        )
        self.assertEqual(
            JobCard.objects.filter(parent_job=job, service_cycle=1).count(),
            0,
        )
        created = BookingScheduleEngine.backfill_missing_day1_children(job)
        self.assertEqual(len(created), 2)
        day1 = {
            c.source_service: c
            for c in JobCard.objects.filter(parent_job=job, service_cycle=1)
        }
        self.assertEqual(set(day1), {'Termite', 'Bed Bugs'})
        self.assertEqual(day1['Termite'].status, JobCard.JobStatus.DONE)
        self.assertEqual(day1['Bed Bugs'].planned_visit_count, 2)
        from core.payment_utils import parse_jobcard_price
        self.assertEqual(parse_jobcard_price(day1['Termite'].price), 2500)

    def test_multi_service_creates_day1_row_per_service(self):
        client = Client.objects.create(
            full_name='Multi User', mobile='9876543401', city='Pune',
        )
        job = JobCard.objects.create(
            client=client,
            service_type='Cockroach, Bed Bugs, Mosquito',
            service_items=[
                {'service': 'Cockroach', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 1500},
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 4000},
                {'service': 'Mosquito', 'plan': 'AMC 3 Services', 'area': '2 BHK', 'amount': 3000},
            ],
            schedule_datetime=datetime(2026, 8, 10, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='8500',
            total_amount=8500,
            reference='Poster',
            client_address='Test address',
            status=JobCard.JobStatus.PENDING,
        )
        created = BookingScheduleEngine.generate_all_visits(job)
        job.refresh_from_db()

        day1 = list(
            JobCard.objects.filter(parent_job=job, service_cycle=1).order_by('service_type')
        )
        self.assertEqual(len(day1), 3)
        names = [c.service_type for c in day1]
        self.assertEqual(names, ['Bed Bugs', 'Cockroach', 'Mosquito'])

        by_name = {c.service_type: c for c in day1}
        from core.payment_utils import parse_jobcard_price
        self.assertEqual(parse_jobcard_price(by_name['Cockroach'].price), parse_jobcard_price('1500'))
        self.assertEqual(by_name['Cockroach'].planned_visit_count, 1)
        self.assertEqual(by_name['Bed Bugs'].planned_visit_count, 2)
        self.assertEqual(by_name['Mosquito'].planned_visit_count, 3)
        self.assertEqual(by_name['Mosquito'].service_category, JobCard.ServiceCategory.AMC)

        # Bed Bugs cycle 2 + Mosquito cycles 2–3 are future visits
        self.assertTrue(
            JobCard.objects.filter(
                parent_job=job, source_service='Bed Bugs', service_cycle=2,
            ).exists()
        )
        self.assertEqual(
            JobCard.objects.filter(parent_job=job, source_service='Mosquito').count(),
            3,
        )
        self.assertEqual(job.visit_type, 'MULTI SERVICE PACKAGE')
        # More than 3 day-1 rows were created (includes follow-ups)
        self.assertGreaterEqual(len(created), 3 + 1 + 2)

    def test_multi_service_ledger_rows_are_separate_not_combined(self):
        from decimal import Decimal

        from django.test import override_settings

        from core.models import Technician
        from core.payout_engine import calculate_and_apply_payout
        from core.technician_ledger import exclude_package_shells, serialize_ledger_row
        from partner.models import Partner

        with override_settings(REVENUE_MODEL_V2=True):
            client = Client.objects.create(
                full_name='Ledger Multi', mobile='9876543402', city='Pune',
            )
            tech = Technician.objects.create(
                name='Tech Multi',
                mobile='9111111101',
                technician_type=Technician.TechnicianType.PARTNER,
            )
            partner = Partner.objects.create(
                full_name='Tech Multi',
                mobile='9111111101',
                password='x',
                core_technician=tech,
                is_app_approved=True,
            )
            partner.set_password('testpass')
            partner.save()

            shell = JobCard.objects.create(
                client=client,
                service_type='Cockroach, Bed Bugs, Mosquito',
                service_items=[
                    {'service': 'Cockroach', 'plan': 'One Time Service', 'amount': 1000},
                    {'service': 'Bed Bugs', 'plan': 'One Time Service', 'amount': 2000},
                    {'service': 'Mosquito', 'plan': 'AMC 3 Services', 'amount': 3000},
                ],
                schedule_datetime=datetime(2026, 8, 10, 10, 0, tzinfo=dt_timezone.utc),
                time_slot='10:00 AM',
                price='6000',
                total_amount=Decimal('6000.00'),
                technician=tech,
                partner=partner,
                payment_model=JobCard.PaymentModel.REVENUE_SHARING,
                payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
                reference='Poster',
                client_address='Test address',
                status=JobCard.JobStatus.PENDING,
            )
            BookingScheduleEngine.generate_all_visits(shell)
            shell.status = JobCard.JobStatus.DONE
            shell.save(update_fields=['status', 'updated_at'])
            BookingScheduleEngine.sync_multi_service_day1_children(shell, completing=True)
            calculate_and_apply_payout(shell, force=True)
            shell.refresh_from_db()
            self.assertEqual(shell.payout_status, JobCard.PayoutStatus.NOT_APPLICABLE)

            day1 = list(JobCard.objects.filter(parent_job=shell, service_cycle=1))
            self.assertEqual(len(day1), 3)
            for child in day1:
                child.refresh_from_db()
                self.assertEqual(child.status, JobCard.JobStatus.DONE)
                calculate_and_apply_payout(child, force=True)
                child.refresh_from_db()

            cockroach = next(c for c in day1 if c.service_type == 'Cockroach')
            bed = next(c for c in day1 if c.service_type == 'Bed Bugs')
            mosquito = next(c for c in day1 if c.service_type == 'Mosquito')
            self.assertEqual(cockroach.visit_revenue_amount, Decimal('1000.00'))
            self.assertEqual(cockroach.technician_pool_amount, Decimal('400.00'))
            # Bed Bugs: 2000 / 2 = 1000 visit revenue → 400 tech
            self.assertEqual(bed.visit_revenue_amount, Decimal('1000.00'))
            self.assertEqual(bed.technician_pool_amount, Decimal('400.00'))
            # Mosquito AMC: 3000 / 3 = 1000 → 400 tech
            self.assertEqual(mosquito.visit_revenue_amount, Decimal('1000.00'))
            self.assertEqual(mosquito.technician_pool_amount, Decimal('400.00'))

            rows = [
                serialize_ledger_row(j, tech)
                for j in exclude_package_shells(day1 + [shell])
            ]
            service_types = sorted(r['service_type'] for r in rows)
            self.assertEqual(service_types, ['Bed Bugs', 'Cockroach', 'Mosquito'])
            self.assertNotIn('Cockroach, Bed Bugs, Mosquito', service_types)

    def test_backfill_skips_when_cancelled_day1_already_exists(self):
        """Regression: cancelled day-1 rows must not trigger UniqueViolation insert."""
        client = Client.objects.create(
            full_name='Cancel Multi', mobile='9876543403', city='Mumbai',
        )
        job = JobCard.objects.create(
            client=client,
            service_type='Bed Bugs, Cockroach / Ants',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '4 BHK', 'amount': 4000},
                {'service': 'Cockroach / Ants', 'plan': 'One Time Service', 'area': '4 BHK', 'amount': 2000},
            ],
            schedule_datetime=datetime(2026, 8, 18, 10, 0, tzinfo=dt_timezone.utc),
            time_slot='10:00 AM',
            price='6000',
            total_amount=6000,
            reference='Poster',
            client_address='Malad',
            status=JobCard.JobStatus.CANCELLED,
        )
        JobCard.objects.create(
            client=client,
            parent_job=job,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_cycle=1,
            max_cycle=2,
            schedule_datetime=job.schedule_datetime,
            status=JobCard.JobStatus.CANCELLED,
            price='4000',
            total_amount=4000,
            is_auto_generated=True,
        )
        JobCard.objects.create(
            client=client,
            parent_job=job,
            service_type='Cockroach / Ants',
            source_service='Cockroach / Ants',
            service_cycle=1,
            max_cycle=1,
            schedule_datetime=job.schedule_datetime,
            status=JobCard.JobStatus.CANCELLED,
            price='2000',
            total_amount=2000,
            is_auto_generated=True,
        )
        created = BookingScheduleEngine.backfill_missing_day1_children(job)
        self.assertEqual(created, [])
        self.assertEqual(
            JobCard.objects.filter(parent_job=job, service_cycle=1).count(),
            2,
        )

    def test_sync_completing_revives_cancelled_day1_children(self):
        client = Client.objects.create(
            full_name='Revive Multi', mobile='9876543404', city='Mumbai',
        )
        job = JobCard.objects.create(
            client=client,
            service_type='Bed Bugs, Cockroach / Ants',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'amount': 4000},
                {'service': 'Cockroach / Ants', 'plan': 'One Time Service', 'amount': 2000},
            ],
            schedule_datetime=datetime(2026, 8, 18, 13, 0, tzinfo=dt_timezone.utc),
            time_slot='01:00 PM',
            price='6000',
            total_amount=6000,
            reference='Poster',
            client_address='Malad',
            status=JobCard.JobStatus.DONE,
            completed_at=datetime(2026, 8, 18, 14, 0, tzinfo=dt_timezone.utc),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
        )
        bed = JobCard.objects.create(
            client=client,
            parent_job=job,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_cycle=1,
            max_cycle=2,
            schedule_datetime=job.schedule_datetime,
            status=JobCard.JobStatus.CANCELLED,
            price='4000',
            total_amount=4000,
            is_auto_generated=True,
        )
        cock = JobCard.objects.create(
            client=client,
            parent_job=job,
            service_type='Cockroach / Ants',
            source_service='Cockroach / Ants',
            service_cycle=1,
            max_cycle=1,
            schedule_datetime=job.schedule_datetime,
            status=JobCard.JobStatus.CANCELLED,
            price='2000',
            total_amount=2000,
            is_auto_generated=True,
        )
        synced = BookingScheduleEngine.sync_multi_service_day1_children(
            job, completing=True
        )
        self.assertEqual(len(synced), 2)
        bed.refresh_from_db()
        cock.refresh_from_db()
        self.assertEqual(bed.status, JobCard.JobStatus.DONE)
        self.assertEqual(cock.status, JobCard.JobStatus.DONE)
        self.assertIsNotNone(bed.completed_at)

