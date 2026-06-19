from decimal import Decimal

from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import BookingPayment, Client, JobCard
from core.payment_utils import (
    derive_payment_status,
    parse_jobcard_price,
    requires_payment_on_completion,
    resolve_completion_amounts,
    validate_payment_amounts,
)
from core.services import JobCardService


class PaymentUtilsTests(TestCase):
    def test_parse_jobcard_price(self):
        self.assertEqual(parse_jobcard_price('₹2,000'), Decimal('2000.00'))
        self.assertEqual(parse_jobcard_price('1500'), Decimal('1500.00'))

    def test_full_payment_amounts(self):
        paid, pending = resolve_completion_amounts(Decimal('2000'), 'full')
        self.assertEqual(paid, Decimal('2000.00'))
        self.assertEqual(pending, Decimal('0.00'))

    def test_half_payment_amounts(self):
        paid, pending = resolve_completion_amounts(Decimal('2000'), 'half')
        self.assertEqual(paid, Decimal('1000.00'))
        self.assertEqual(pending, Decimal('1000.00'))

    def test_custom_pending_amount(self):
        paid, pending = resolve_completion_amounts(
            Decimal('2000'), 'custom', pending_amount=Decimal('500'),
        )
        self.assertEqual(paid, Decimal('1500.00'))
        self.assertEqual(pending, Decimal('500.00'))

    def test_custom_paid_amount(self):
        paid, pending = resolve_completion_amounts(
            Decimal('2000'), 'custom', paid_amount=Decimal('1200'),
        )
        self.assertEqual(paid, Decimal('1200.00'))
        self.assertEqual(pending, Decimal('800.00'))

    def test_validation_rejects_negative(self):
        with self.assertRaises(Exception):
            validate_payment_amounts(Decimal('100'), Decimal('-1'), Decimal('101'))

    def test_validation_rejects_exceeding_total(self):
        with self.assertRaises(Exception):
            validate_payment_amounts(Decimal('100'), Decimal('80'), Decimal('30'))

    def test_derive_payment_status(self):
        self.assertEqual(
            derive_payment_status(Decimal('2000'), Decimal('0'), Decimal('2000')),
            JobCard.PaymentStatus.PAID,
        )
        self.assertEqual(
            derive_payment_status(Decimal('1000'), Decimal('1000'), Decimal('2000')),
            JobCard.PaymentStatus.PARTIALLY_PAID,
        )
        self.assertEqual(
            derive_payment_status(Decimal('0'), Decimal('2000'), Decimal('2000')),
            JobCard.PaymentStatus.PENDING,
        )


class PaymentCollectionAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='staff', password='pass1234')
        self.client_record = Client.objects.create(full_name='Test Client', mobile='9876543210')
        self.job = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach',
            schedule_datetime=datetime(2026, 6, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='2000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            master_location_id=None,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_complete_booking_half_payment(self):
        response = self.api.patch(
            f'/api/v1/jobcards/{self.job.id}/',
            {
                'status': 'Done',
                'payment_mode': 'Cash',
                'payment_collection_type': 'half',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.job.refresh_from_db()
        self.assertEqual(self.job.paid_amount, Decimal('1000.00'))
        self.assertEqual(self.job.pending_amount, Decimal('1000.00'))
        self.assertEqual(self.job.payment_status, JobCard.PaymentStatus.PARTIALLY_PAID)
        self.assertEqual(BookingPayment.objects.filter(jobcard=self.job).count(), 1)

    def test_complete_bed_bug_booking_creates_follow_up_without_error(self):
        """Bed Bug cycle bookings use next_service_date (date) for follow-ups — must not 500."""
        from datetime import timedelta

        schedule = self.job.schedule_datetime
        self.job.service_type = 'Bed Bugs'
        self.job.service_category = JobCard.ServiceCategory.ONE_TIME
        self.job.next_service_date = (schedule + timedelta(days=15)).date()
        self.job.max_cycle = 2
        self.job.service_cycle = 1
        self.job.price = '3000'
        self.job.save()

        response = self.api.patch(
            f'/api/v1/jobcards/{self.job.id}/',
            {
                'status': 'Done',
                'payment_mode': 'Online',
                'payment_collection_type': 'full',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, JobCard.JobStatus.DONE)
        self.assertEqual(self.job.paid_amount, Decimal('3000.00'))
        follow_up = JobCard.objects.filter(parent_job=self.job, service_cycle=2).first()
        self.assertIsNotNone(follow_up)
        self.assertIsNotNone(follow_up.schedule_datetime)

    def test_collect_pending_payment(self):
        JobCardService.apply_completion_payment(
            self.job,
            user=self.user,
            payment_mode='Cash',
            collection_type='half',
        )
        self.job.status = JobCard.JobStatus.DONE
        self.job.save(update_fields=['status'])

        response = self.api.post(
            f'/api/v1/pending-payments/{self.job.id}/collect/',
            {'amount': '1000', 'payment_mode': 'Online', 'remarks': 'Final settlement'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.job.refresh_from_db()
        self.assertEqual(self.job.pending_amount, Decimal('0.00'))
        self.assertEqual(self.job.paid_amount, Decimal('2000.00'))
        self.assertEqual(self.job.payment_status, JobCard.PaymentStatus.PAID)


class RequiresPaymentOnCompletionTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(full_name='Test Client', mobile='9876543211')
        self.main = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 6, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='3000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            service_cycle=1,
        )
        self.follow_up = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 9, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='0',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=self.main,
            service_cycle=2,
            is_followup_visit=True,
            included_in_amc=True,
            is_service_call=True,
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
            booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
            payment_status=JobCard.PaymentStatus.PAID,
        )
        self.complaint = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 7, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='0',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            is_complaint_call=True,
            complaint_parent_booking=self.main,
            booking_type=JobCard.BookingType.COMPLAINT_CALL,
            booking_category=JobCard.BookingCategory.COMPLAINT_CALL,
        )

    def test_main_booking_requires_payment(self):
        self.assertTrue(requires_payment_on_completion(self.main))

    def test_amc_follow_up_does_not_require_payment(self):
        self.assertFalse(requires_payment_on_completion(self.follow_up))

    def test_complaint_does_not_require_payment(self):
        self.assertFalse(requires_payment_on_completion(self.complaint))


class PaymentCollectionSkipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='staff2', password='pass1234')
        self.client_record = Client.objects.create(full_name='Follow Client', mobile='9876543212')
        self.main = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 6, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='2200',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            service_cycle=1,
            paid_amount=Decimal('2200.00'),
            pending_amount=Decimal('0.00'),
            payment_status=JobCard.PaymentStatus.PAID,
        )
        self.follow_up = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 9, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='0',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            service_category=JobCard.ServiceCategory.AMC,
            parent_job=self.main,
            service_cycle=2,
            is_followup_visit=True,
            included_in_amc=True,
            is_service_call=True,
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
            booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
            payment_status=JobCard.PaymentStatus.PAID,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_complete_amc_follow_up_without_payment_payload(self):
        response = self.api.patch(
            f'/api/v1/jobcards/{self.follow_up.id}/',
            {'status': 'Done'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.follow_up.refresh_from_db()
        self.assertEqual(self.follow_up.status, JobCard.JobStatus.DONE)
        self.assertEqual(BookingPayment.objects.filter(jobcard=self.follow_up).count(), 0)

    def test_complete_main_booking_without_payment_payload_rejected(self):
        pending_main = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 8, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='2500',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            service_cycle=1,
        )
        response = self.api.patch(
            f'/api/v1/jobcards/{pending_main.id}/',
            {'status': 'Done'},
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.data)
        pending_main.refresh_from_db()
        self.assertEqual(pending_main.status, JobCard.JobStatus.PENDING)


class PendingPaymentReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='staff3', password='pass1234')
        self.client_record = Client.objects.create(full_name='Pending Client', mobile='9876543213')
        self.main_done = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 3, 15, 10, 0, tzinfo=dt_timezone.utc),
            price='2000',
            total_amount=Decimal('2000.00'),
            paid_amount=Decimal('1000.00'),
            pending_amount=Decimal('1000.00'),
            reference='Other',
            status=JobCard.JobStatus.DONE,
            payment_status=JobCard.PaymentStatus.PARTIALLY_PAID,
        )
        self.follow_up_done = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=datetime(2026, 4, 15, 10, 0, tzinfo=dt_timezone.utc),
            price='0',
            total_amount=Decimal('0.00'),
            paid_amount=Decimal('500.00'),
            pending_amount=Decimal('500.00'),
            reference='Other',
            status=JobCard.JobStatus.DONE,
            is_followup_visit=True,
            included_in_amc=True,
            booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
            payment_status=JobCard.PaymentStatus.PARTIALLY_PAID,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_pending_list_excludes_amc_follow_up(self):
        response = self.api.get('/api/v1/pending-payments/')
        self.assertEqual(response.status_code, 200, response.data)
        ids = [row['id'] for row in response.data['results']]
        self.assertIn(self.main_done.id, ids)
        self.assertNotIn(self.follow_up_done.id, ids)

    def test_stats_respect_outstanding_bookings_only(self):
        response = self.api.get('/api/v1/pending-payments/stats/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['total_pending_bookings'], 1)
        self.assertEqual(Decimal(str(response.data['total_outstanding_amount'])), Decimal('1000.00'))
        self.assertEqual(Decimal(str(response.data['total_collected_amount'])), Decimal('1000.00'))
