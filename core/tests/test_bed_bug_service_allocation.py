"""Bed Bugs / multi-visit: payout on Done even when payment is not collected again."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Client, JobCard, Technician
from core.payout_engine import calculate_and_apply_payout
from core.management.commands.heal_bed_bug_packages import heal_orphan_bed_bug_second_visits
from partner.models import Partner


@override_settings(REVENUE_MODEL_V2=True)
class BedBugServiceAllocationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bedbug_admin', password='pass1234', is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_obj = Client.objects.create(full_name='Wahid Test', mobile='8779662142')
        self.tech1 = Technician.objects.create(
            name='Sohil', mobile='9000000001',
            technician_type=Technician.TechnicianType.PARTNER, is_active=True,
        )
        self.tech2 = Technician.objects.create(
            name='Mustafa', mobile='9000000002',
            technician_type=Technician.TechnicianType.PARTNER, is_active=True,
        )
        Partner.objects.create(
            full_name='Sohil', mobile='9000000001', password='x',
            core_technician=self.tech1, is_app_approved=True,
        )
        Partner.objects.create(
            full_name='Mustafa', mobile='9000000002', password='x',
            core_technician=self.tech2, is_app_approved=True,
        )

    def _bed_bug_root(self, **overrides):
        fields = {
            'client': self.client_obj,
            'technician': self.tech1,
            'service_type': 'Bed Bugs',
            'source_service': 'Bed Bugs',
            'visit_type': 'BED BUG SERVICE',
            'city': 'Mumbai',
            'job_type': JobCard.JobType.CUSTOMER,
            'booking_type': JobCard.BookingType.NEW_BOOKING,
            'price': '3000',
            'total_amount': Decimal('3000.00'),
            'status': JobCard.JobStatus.PENDING,
            'schedule_datetime': timezone.now() - timezone.timedelta(days=10),
            'max_cycle': 2,
            'planned_visit_count': 2,
            'service_cycle': 1,
            'payment_model': JobCard.PaymentModel.REVENUE_SHARING,
            'payout_status': JobCard.PayoutStatus.PENDING,
            'technician_share_percent': Decimal('40.00'),
            'created_by': self.user,
            'service_items': [
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '2 BHK', 'amount': 3000},
            ],
        }
        fields.update(overrides)
        return JobCard.objects.create(**fields)

    def test_visit1_done_with_payment_allocates_half_package_to_tech(self):
        root = self._bed_bug_root()
        res = self.api.patch(
            f'/api/v1/jobcards/{root.id}/',
            {
                'status': 'Done',
                'payment_mode': 'Cash',
                'payment_collection_type': 'full',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        root.refresh_from_db()
        self.assertEqual(root.visit_revenue_amount, Decimal('1500.00'))
        self.assertEqual(root.visit_payout_amount, Decimal('600.00'))
        self.assertEqual(root.paid_amount, Decimal('3000.00'))

    def test_visit2_done_without_payment_still_gets_payout(self):
        root = self._bed_bug_root(status=JobCard.JobStatus.DONE, payment_status=JobCard.PaymentStatus.PAID)
        calculate_and_apply_payout(root, force=True)
        root.refresh_from_db()
        visit2 = JobCard.objects.create(
            client=self.client_obj,
            technician=self.tech2,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            parent_job=root,
            is_followup_visit=True,
            is_service_call=True,
            booking_type=JobCard.BookingType.SERVICE_CALL,
            booking_category=JobCard.BookingCategory.SERVICE_CALL,
            price='0',
            total_amount=Decimal('0.00'),
            status=JobCard.JobStatus.UPCOMING,
            schedule_datetime=timezone.now(),
            service_cycle=2,
            max_cycle=2,
            planned_visit_count=2,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.PENDING,
            technician_share_percent=Decimal('40.00'),
            payment_status=JobCard.PaymentStatus.PAID,
            created_by=self.user,
        )
        res = self.api.patch(
            f'/api/v1/jobcards/{visit2.id}/',
            {'status': 'Done'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        visit2.refresh_from_db()
        self.assertEqual(visit2.visit_revenue_amount, Decimal('1500.00'))
        self.assertEqual(visit2.visit_payout_amount, Decimal('600.00'))

    def test_heal_orphan_second_visit_relinks_and_clears_duplicate_payment(self):
        root = self._bed_bug_root(
            status=JobCard.JobStatus.DONE,
            payment_status=JobCard.PaymentStatus.PAID,
            paid_amount=Decimal('3000.00'),
        )
        calculate_and_apply_payout(root, force=True)
        placeholder = JobCard.objects.create(
            client=self.client_obj,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            parent_job=root,
            is_followup_visit=True,
            booking_type=JobCard.BookingType.SERVICE_CALL,
            booking_category=JobCard.BookingCategory.SERVICE_CALL,
            price='0',
            status=JobCard.JobStatus.UPCOMING,
            schedule_datetime=timezone.now() + timezone.timedelta(days=5),
            service_cycle=2,
            max_cycle=2,
            creation_source=JobCard.CreationSource.AMC_AUTO,
            created_by=self.user,
        )
        orphan = JobCard.objects.create(
            client=self.client_obj,
            technician=self.tech2,
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            price='00.00',
            total_amount=Decimal('3000.00'),
            paid_amount=Decimal('3000.00'),
            status=JobCard.JobStatus.DONE,
            schedule_datetime=timezone.now(),
            service_cycle=1,
            max_cycle=2,
            planned_visit_count=2,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.PENDING,
            technician_share_percent=Decimal('40.00'),
            payment_status=JobCard.PaymentStatus.PAID,
            created_by=self.user,
        )
        result = heal_orphan_bed_bug_second_visits(dry_run=False)
        orphan.refresh_from_db()
        placeholder.refresh_from_db()
        self.assertEqual(orphan.parent_job_id, root.id)
        self.assertEqual(orphan.service_cycle, 2)
        self.assertTrue(orphan.is_followup_visit)
        self.assertEqual(orphan.paid_amount, Decimal('0.00'))
        self.assertEqual(placeholder.status, JobCard.JobStatus.CANCELLED)
        self.assertEqual(orphan.visit_payout_amount, Decimal('600.00'))
        self.assertGreaterEqual(result['linked'], 1)

    def test_heal_allocation_fixes_legacy_exempt_zero_payout(self):
        from core.management.commands.heal_bed_bug_packages import heal_bed_bug_visit_allocations

        root = self._bed_bug_root(
            status=JobCard.JobStatus.DONE,
            payment_status=JobCard.PaymentStatus.PAID,
            paid_amount=Decimal('3000.00'),
            payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT,
            visit_revenue_amount=Decimal('0.00'),
            visit_payout_amount=Decimal('0.00'),
        )
        result = heal_bed_bug_visit_allocations(dry_run=False)
        root.refresh_from_db()
        self.assertGreaterEqual(result['fixed'], 1)
        self.assertEqual(root.visit_revenue_amount, Decimal('1500.00'))
        self.assertEqual(root.visit_payout_amount, Decimal('600.00'))
        self.assertNotEqual(root.payout_status, JobCard.PayoutStatus.LEGACY_EXEMPT)
