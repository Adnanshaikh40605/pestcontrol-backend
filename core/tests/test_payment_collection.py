from decimal import Decimal

from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import BookingPayment, Client, JobCard
from core.payment_utils import (
    derive_payment_status,
    parse_jobcard_price,
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
