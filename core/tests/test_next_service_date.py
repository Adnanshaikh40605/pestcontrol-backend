"""Cross-check tests for next service date rules and completion follow-ups."""
from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.jobcard_schedule import schedule_datetime_from_service_date
from core.models import Client, JobCard, Renewal
from core.services import JobCardService, RenewalService


class NextServiceDateRulesTests(TestCase):
    def setUp(self):
        self.schedule = datetime(2026, 6, 1, 10, 30, tzinfo=dt_timezone.utc)

    def test_cockroach_amc_next_date_and_cycles(self):
        job = JobCard(
            service_type='Cockroach / Ants',
            service_category=JobCard.ServiceCategory.AMC,
            schedule_datetime=self.schedule,
        )
        next_date, max_cycle = JobCardService.calculate_next_service_date(job)
        self.assertEqual(max_cycle, 3)
        self.assertEqual(next_date, date(2026, 10, 1))

    def test_bed_bugs_label_variants(self):
        for label in ('Bed Bugs', 'Bed Bug', 'BedBug'):
            job = JobCard(service_type=label, schedule_datetime=self.schedule)
            next_date, max_cycle = JobCardService.calculate_next_service_date(job)
            self.assertEqual(max_cycle, 2, msg=label)
            self.assertEqual(next_date, date(2026, 6, 16), msg=label)

    def test_service_items_cockroach_amc_priority_over_bed_bug(self):
        job = JobCard(
            service_type='Cockroach / Ants, Bed Bugs',
            service_category=JobCard.ServiceCategory.AMC,
            schedule_datetime=self.schedule,
            service_items=[
                {'service': 'Cockroach / Ants', 'plan': 'AMC 3 Services', 'area': '2 BHK', 'amount': 2500},
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 3000},
            ],
        )
        next_date, max_cycle = JobCardService.calculate_next_service_date(job)
        self.assertEqual(max_cycle, 3)
        self.assertEqual(next_date, date(2026, 10, 1))

    def test_ensure_next_service_schedule_fills_missing_date(self):
        client = Client.objects.create(full_name='Test', mobile='9111111111')
        job = JobCard.objects.create(
            client=client,
            service_type='Bed Bugs',
            schedule_datetime=self.schedule,
            price='3000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
        )
        self.assertIsNone(job.next_service_date)
        JobCardService.ensure_next_service_schedule(job)
        job.refresh_from_db()
        self.assertEqual(job.max_cycle, 2)
        self.assertEqual(job.next_service_date, date(2026, 6, 16))


class ScheduleDatetimeFromServiceDateTests(TestCase):
    def test_converts_date_with_time_slot(self):
        import pytz

        ist = pytz.timezone('Asia/Kolkata')
        ref = ist.localize(datetime(2026, 6, 1, 10, 30, 0)).astimezone(dt_timezone.utc)
        result = schedule_datetime_from_service_date(
            date(2026, 6, 16),
            reference_datetime=ref,
            time_slot='2:00 PM',
        )
        local = result.astimezone(ist)
        self.assertEqual(local.date(), date(2026, 6, 16))
        self.assertEqual(local.hour, 14)
        self.assertEqual(local.minute, 0)


class CompletionFollowUpTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='staff2', password='pass1234')
        self.client_record = Client.objects.create(full_name='Follow Up Client', mobile='9222222222')
        self.schedule = datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_complete_without_preset_next_date_still_creates_follow_up(self):
        """Legacy bookings missing next_service_date must still spawn visit 2."""
        job = JobCard.objects.create(
            client=self.client_record,
            service_type='Bed Bugs',
            schedule_datetime=self.schedule,
            time_slot='11:00 AM',
            price='3000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
        )
        self.assertIsNone(job.next_service_date)

        response = self.api.patch(
            f'/api/v1/jobcards/{job.id}/',
            {'status': 'Done', 'payment_mode': 'Online', 'payment_collection_type': 'full'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        job.refresh_from_db()
        self.assertEqual(job.status, JobCard.JobStatus.DONE)
        self.assertEqual(job.next_service_date, date(2026, 6, 16))

        follow_up = JobCard.objects.get(parent_job=job, service_cycle=2)
        self.assertEqual(follow_up.status, JobCard.JobStatus.UPCOMING)
        self.assertEqual(follow_up.included_in_amc, False)
        self.assertEqual(follow_up.booking_category, JobCard.BookingCategory.SERVICE_CALL)
        self.assertIsNotNone(follow_up.schedule_datetime)
        self.assertEqual(follow_up.time_slot, '11:00 AM')

        import pytz

        ist = pytz.timezone('Asia/Kolkata')
        local = follow_up.schedule_datetime.astimezone(ist)
        self.assertEqual(local.date(), date(2026, 6, 16))
        self.assertEqual(local.hour, 11)

    def test_cockroach_amc_chain_sets_third_visit_date_on_second_job(self):
        job = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            service_category=JobCard.ServiceCategory.AMC,
            schedule_datetime=self.schedule,
            next_service_date=date(2026, 10, 1),
            max_cycle=3,
            service_cycle=1,
            price='5000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
        )

        response = self.api.patch(
            f'/api/v1/jobcards/{job.id}/',
            {'status': 'Done', 'payment_mode': 'Cash', 'payment_collection_type': 'full'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        visit2 = JobCard.objects.get(parent_job=job, service_cycle=2)
        self.assertEqual(visit2.next_service_date, date(2027, 2, 1))
        self.assertEqual(visit2.max_cycle, 3)
        self.assertEqual(visit2.included_in_amc, True)
        self.assertEqual(visit2.booking_category, JobCard.BookingCategory.AMC_FOLLOWUP)


class RenewalGenerationTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(full_name='Renewal Test', mobile='9333333333')
        self.schedule = datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)

    def test_multi_visit_jobs_do_not_create_contract_renewals(self):
        job = JobCard.objects.create(
            client=self.client_record,
            service_type='Bed Bugs',
            schedule_datetime=self.schedule,
            next_service_date=date(2026, 6, 16),
            max_cycle=2,
            price='3000',
            reference='Other',
        )
        renewals = RenewalService.generate_renewals_for_jobcard(job)
        self.assertEqual(renewals, [])
