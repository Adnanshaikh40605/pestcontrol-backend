"""Complaint call creation must not spawn package follow-ups or inflate booking counts."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.complaint_service import (
    create_complaint_jobcard,
    heal_complaint_jobs,
    history_root_id,
    is_billable_root_booking,
)
from core.models import Client, JobCard, Technician
from core.services import JobCardService


@override_settings(REVENUE_MODEL_V2=True)
class ComplaintCallCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='complaint_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_obj = Client.objects.create(
            full_name='Veena Test',
            mobile='9111000099',
        )
        self.tech = Technician.objects.create(
            name='Complaint Tech',
            mobile='9111000088',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        self.parent = JobCard.objects.create(
            client=self.client_obj,
            technician=self.tech,
            service_type='Bed Bugs',
            city='Pune',
            job_type=JobCard.JobType.CUSTOMER,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            price='2500',
            total_amount=Decimal('2500.00'),
            status=JobCard.JobStatus.DONE,
            schedule_datetime=timezone.now() - timezone.timedelta(days=5),
            max_cycle=2,
            service_cycle=1,
            payment_status=JobCard.PaymentStatus.PAID,
            created_by=self.user,
        )
        self.followup = JobCard.objects.create(
            client=self.client_obj,
            technician=self.tech,
            service_type='Bed Bugs',
            city='Pune',
            parent_job=self.parent,
            is_followup_visit=True,
            is_service_call=True,
            booking_type=JobCard.BookingType.SERVICE_CALL,
            booking_category=JobCard.BookingCategory.SERVICE_CALL,
            price='0',
            total_amount=Decimal('0.00'),
            status=JobCard.JobStatus.UPCOMING,
            schedule_datetime=timezone.now() + timezone.timedelta(days=10),
            service_cycle=2,
            max_cycle=2,
            is_auto_generated=True,
            creation_source=JobCard.CreationSource.AMC_AUTO,
            created_by=self.user,
        )

    def test_create_complaint_api_links_parent_and_stays_single_service(self):
        res = self.api.post(
            '/api/v1/complaints/create_complaint/',
            {
                'parent_booking_id': self.parent.id,
                'complaint_type': 'Bed Bugs Still Active',
                'complaint_note': 'Still seeing bugs',
                'priority': 'Medium',
                'revisit_date': timezone.localdate().isoformat(),
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        complaint = JobCard.objects.get(pk=res.data['id'])
        self.assertTrue(complaint.is_complaint_call)
        self.assertEqual(complaint.complaint_parent_booking_id, self.parent.id)
        self.assertIsNone(complaint.parent_job_id)
        self.assertEqual(complaint.price, '0')
        self.assertEqual(complaint.total_amount, Decimal('0.00'))
        self.assertEqual(complaint.max_cycle, 1)
        self.assertIsNone(complaint.next_service_date)
        self.assertEqual(res.data.get('price_display'), 'Free (Complaint)')
        self.assertFalse(
            JobCard.objects.filter(parent_job=complaint).exists(),
            'Creating a complaint must not spawn follow-up services',
        )

    def test_completing_complaint_does_not_create_bed_bug_followup(self):
        complaint = create_complaint_jobcard(
            parent=self.parent,
            complaint_type='Need Revisit',
            complaint_note='Please revisit',
            created_by=self.user,
        )
        # Simulate legacy bad state that used to spawn visit 2.
        JobCard.objects.filter(pk=complaint.pk).update(
            max_cycle=2,
            next_service_date=timezone.localdate() + timezone.timedelta(days=15),
            service_type='Bed Bugs',
            status=JobCard.JobStatus.PENDING,
        )
        complaint.refresh_from_db()
        complaint.status = JobCard.JobStatus.DONE
        complaint.save(update_fields=['status'])
        created = JobCardService.handle_job_completion(complaint)
        self.assertIsNone(created)
        self.assertFalse(
            JobCard.objects.filter(parent_job=complaint).exclude(
                status=JobCard.JobStatus.CANCELLED,
            ).exists()
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.max_cycle, 1)
        self.assertIsNone(complaint.next_service_date)

    def test_customer_history_groups_and_excludes_complaint_from_booking_count(self):
        complaint = create_complaint_jobcard(
            parent=self.parent,
            complaint_type='Need Revisit',
            complaint_note='Please revisit',
            created_by=self.user,
        )
        res = self.api.get(f'/api/v1/customer-history/{self.client_obj.id}/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['stats']['total_bookings'], 1)
        by_id = {row['id']: row for row in res.data['bookings']}
        self.assertEqual(by_id[complaint.id]['history_role'], 'complaint')
        self.assertEqual(by_id[complaint.id]['root_booking_id'], self.parent.id)
        self.assertEqual(by_id[self.followup.id]['history_role'], 'service')
        self.assertEqual(by_id[self.followup.id]['root_booking_id'], self.parent.id)
        self.assertEqual(by_id[self.parent.id]['history_role'], 'booking')
        self.assertTrue(is_billable_root_booking(self.parent))
        self.assertEqual(history_root_id(complaint), self.parent.id)

    def test_cancelled_linked_visits_do_not_inflate_booking_count(self):
        """Ghanshyam-style: cancelled check-ups stay under the root booking."""
        for cycle in (2, 3, 4, 5):
            JobCard.objects.create(
                client=self.client_obj,
                service_type='Termite',
                source_service='Termite',
                visit_type='TERMITE CHECK-UP',
                city='Mumbai',
                parent_job=self.parent,
                is_followup_visit=True,
                is_auto_generated=True,
                booking_type=JobCard.BookingType.SERVICE_CALL,
                booking_category=JobCard.BookingCategory.SERVICE_CALL,
                price='0',
                status=JobCard.JobStatus.CANCELLED,
                schedule_datetime=timezone.now() + timezone.timedelta(days=30 * cycle),
                service_cycle=cycle,
                max_cycle=5,
                planned_visit_count=5,
                creation_source=JobCard.CreationSource.AMC_AUTO,
                created_by=self.user,
                cancellation_reason='Not required',
            )
        res = self.api.get(f'/api/v1/customer-history/{self.client_obj.id}/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['stats']['total_bookings'], 1)
        cancelled = [row for row in res.data['bookings'] if row['status'] == 'Cancelled']
        self.assertGreaterEqual(len(cancelled), 4)
        for row in cancelled:
            self.assertEqual(row['history_role'], 'service')
            self.assertEqual(row['root_booking_id'], self.parent.id)

    def test_heal_links_orphan_complaint_and_cancels_spurious_followup(self):
        orphan = JobCard.objects.create(
            client=self.client_obj,
            service_type='Bed Bugs',
            city='Pune',
            is_complaint_call=True,
            booking_type=JobCard.BookingType.COMPLAINT_CALL,
            booking_category=JobCard.BookingCategory.COMPLAINT_CALL,
            price='3000.0',
            total_amount=Decimal('3000.00'),
            status=JobCard.JobStatus.DONE,
            schedule_datetime=timezone.now() - timezone.timedelta(days=1),
            max_cycle=2,
            service_cycle=1,
            next_service_date=timezone.localdate() + timezone.timedelta(days=14),
            created_by=self.user,
        )
        spurious = JobCard.objects.create(
            client=self.client_obj,
            service_type='Bed Bugs',
            city='Pune',
            parent_job=orphan,
            is_followup_visit=True,
            booking_type=JobCard.BookingType.SERVICE_CALL,
            booking_category=JobCard.BookingCategory.SERVICE_CALL,
            price='0',
            status=JobCard.JobStatus.UPCOMING,
            schedule_datetime=timezone.now() + timezone.timedelta(days=14),
            service_cycle=2,
            max_cycle=2,
            creation_source=JobCard.CreationSource.AMC_AUTO,
            created_by=self.user,
        )
        result = heal_complaint_jobs(dry_run=False)
        orphan.refresh_from_db()
        spurious.refresh_from_db()
        self.assertEqual(orphan.complaint_parent_booking_id, self.parent.id)
        self.assertEqual(orphan.price, '0')
        self.assertEqual(orphan.max_cycle, 1)
        self.assertIsNone(orphan.next_service_date)
        self.assertEqual(spurious.status, JobCard.JobStatus.CANCELLED)
        self.assertIn(spurious.id, result['cancelled_ids'])
