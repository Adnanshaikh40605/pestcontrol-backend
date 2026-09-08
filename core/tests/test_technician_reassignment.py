"""Reassignment must move a booking off the old technician everywhere.

Ledger, booking row, participations, and partner app ownership must all follow
the current JobCard.technician after User 1 -> User 2 reassignment.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    Client,
    JobCard,
    JobCardTechnicianParticipation,
    Technician,
)
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianReassignmentLedgerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reassign_admin', password='pass1234', is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_obj = Client.objects.create(
            full_name='Reassign Customer', mobile='9556000011',
        )
        self.tech1, self.partner1 = self._partner_tech('User One', '9440000011')
        self.tech2, self.partner2 = self._partner_tech('User Two', '9440000012')

    def _partner_tech(self, name, mobile):
        tech = Technician.objects.create(
            name=name,
            mobile=mobile,
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        partner = Partner.objects.create(
            full_name=name,
            mobile=mobile,
            password='x',
            core_technician=tech,
            is_app_approved=True,
        )
        return tech, partner

    def _job(self, *, technician, partner, **overrides):
        now = timezone.now()
        fields = {
            'client': self.client_obj,
            'technician': technician,
            'partner': partner,
            'service_type': 'Cockroach / Ants',
            'city': 'Pune',
            'job_type': JobCard.JobType.CUSTOMER,
            'booking_type': 'New Booking',
            'price': '1000',
            'total_amount': Decimal('1000'),
            'status': JobCard.JobStatus.ON_PROCESS,
            'schedule_datetime': now,
            'assigned_to': technician.name,
            'payment_model': JobCard.PaymentModel.REVENUE_SHARING,
            'payout_status': JobCard.PayoutStatus.PENDING,
            'created_by': self.user,
        }
        fields.update(overrides)
        job = JobCard.objects.create(**fields)
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=technician,
            partner=partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
        )
        return job

    def _assign(self, job, technician):
        return self.api.post(
            f'/api/v1/jobcards/{job.id}/assign/',
            {'technician_id': technician.id},
            format='json',
        )

    def _ledger_rows(self, technician, params=None):
        res = self.api.get(
            f'/api/v1/technicians/{technician.id}/ledger/', params or {},
        )
        self.assertEqual(res.status_code, 200, res.data)
        return res.data['results']

    def _ledger_job_ids(self, technician, params=None):
        return [row['job_id'] for row in self._ledger_rows(technician, params)]

    def test_reassign_moves_single_visit_ledger_row_to_new_technician(self):
        job = self._job(technician=self.tech1, partner=self.partner1)

        res = self._assign(job, self.tech2)
        self.assertEqual(res.status_code, 200, res.data)

        job.refresh_from_db()
        self.assertEqual(job.technician_id, self.tech2.id)
        self.assertEqual(job.assigned_to, 'User Two')
        self.assertEqual(job.partner_id, self.partner2.id)
        self.assertFalse(
            JobCardTechnicianParticipation.objects.filter(
                jobcard=job, technician=self.tech1,
            ).exists()
        )
        self.assertNotIn(job.id, self._ledger_job_ids(self.tech1))
        self.assertIn(job.id, self._ledger_job_ids(self.tech2))

    def test_reassign_updates_assigned_technicians_label(self):
        job = self._job(technician=self.tech1, partner=self.partner1)
        self._assign(job, self.tech2)

        row = next(
            r for r in self._ledger_rows(self.tech2) if r['job_id'] == job.id
        )
        self.assertEqual(row['assigned_technicians'], 'User Two')

    def test_reassign_to_salaried_tech_clears_previous_partner(self):
        """Old partner must lose the job in the partner app, even without a new one."""
        salaried = Technician.objects.create(
            name='Salaried Three',
            mobile='9440000013',
            technician_type=Technician.TechnicianType.SALARIED,
            is_active=True,
        )
        job = self._job(technician=self.tech1, partner=self.partner1)

        res = self._assign(job, salaried)
        self.assertEqual(res.status_code, 200, res.data)

        job.refresh_from_db()
        self.assertEqual(job.technician_id, salaried.id)
        self.assertIsNone(job.partner_id)
        self.assertNotIn(job.id, self._ledger_job_ids(self.tech1))

    def _complete_with_payout(self, job):
        from core.payout_engine import calculate_and_apply_payout

        JobCard.objects.filter(pk=job.pk).update(
            status=JobCard.JobStatus.DONE, completed_at=timezone.now(),
        )
        job.refresh_from_db()
        calculate_and_apply_payout(job, force=True)
        return job

    def test_assign_after_completion_drops_previous_partner_earnings(self):
        job = self._complete_with_payout(
            self._job(technician=self.tech1, partner=self.partner1)
        )
        self.assertTrue(
            PartnerEarning.objects.filter(job=job, partner=self.partner1).exists()
        )

        self._assign(job, self.tech2)

        job.refresh_from_db()
        self.assertEqual(job.technician_id, self.tech2.id)
        self.assertFalse(
            PartnerEarning.objects.filter(job=job, partner=self.partner1).exists()
        )

    def test_booking_edit_reassign_moves_done_visit_earnings(self):
        """Editing the technician on a completed booking must repay User 2."""
        job = self._complete_with_payout(
            self._job(technician=self.tech1, partner=self.partner1)
        )

        res = self.api.patch(
            f'/api/v1/jobcards/{job.id}/',
            {'technician': self.tech2.id},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)

        job.refresh_from_db()
        self.assertEqual(job.technician_id, self.tech2.id)
        self.assertFalse(
            PartnerEarning.objects.filter(job=job, partner=self.partner1).exists()
        )
        self.assertTrue(
            PartnerEarning.objects.filter(job=job, partner=self.partner2).exists()
        )
        self.assertNotIn(job.id, self._ledger_job_ids(self.tech1))
        self.assertIn(job.id, self._ledger_job_ids(self.tech2))

    def test_reassign_package_shell_moves_day1_children(self):
        """Ledger shows per-service child rows — they must follow the new lead."""
        shell = self._job(
            technician=self.tech1,
            partner=self.partner1,
            service_type='Cockroach / Ants, Termite',
            price='3500',
            total_amount=Decimal('3500'),
            service_items=[
                {'service': 'Cockroach / Ants', 'plan': 'One Time Service',
                 'area': '2 BHK', 'amount': '1500'},
                {'service': 'Termite', 'plan': 'One Time Treatment',
                 'area': '2 BHK', 'amount': '2000'},
            ],
        )
        from core.booking_schedule_engine import BookingScheduleEngine

        BookingScheduleEngine.backfill_missing_day1_children(shell)
        children = list(JobCard.objects.filter(parent_job=shell, service_cycle=1))
        self.assertTrue(children)
        for child in children:
            self.assertEqual(child.technician_id, self.tech1.id)

        self._assign(shell, self.tech2)

        for child in JobCard.objects.filter(parent_job=shell, service_cycle=1):
            self.assertEqual(
                child.technician_id, self.tech2.id,
                f'child #{child.id} still on old technician',
            )
            self.assertFalse(
                JobCardTechnicianParticipation.objects.filter(
                    jobcard=child, technician=self.tech1,
                ).exists()
            )

        old_ids = self._ledger_job_ids(self.tech1)
        new_ids = self._ledger_job_ids(self.tech2)
        for child in children:
            self.assertNotIn(child.id, old_ids)
            self.assertIn(child.id, new_ids)

    def test_repeated_reassignment_keeps_only_current_technician(self):
        """User 1 -> User 2 -> User 3 must leave the job only on User 3."""
        tech3, partner3 = self._partner_tech('User Three', '9440000014')
        job = self._job(technician=self.tech1, partner=self.partner1)

        self._assign(job, self.tech2)
        self._assign(job, tech3)

        job.refresh_from_db()
        self.assertEqual(job.technician_id, tech3.id)
        self.assertEqual(job.partner_id, partner3.id)
        self.assertEqual(
            list(
                JobCardTechnicianParticipation.objects.filter(jobcard=job)
                .values_list('technician_id', flat=True)
            ),
            [tech3.id],
        )
        self.assertNotIn(job.id, self._ledger_job_ids(self.tech1))
        self.assertNotIn(job.id, self._ledger_job_ids(self.tech2))
        self.assertIn(job.id, self._ledger_job_ids(tech3))

    def test_reassign_moves_pending_followup_visits(self):
        """Future AMC visits still owned by User 1 must move to User 2."""
        parent = self._job(
            technician=self.tech1,
            partner=self.partner1,
            service_category=JobCard.ServiceCategory.AMC,
            price='7000',
            total_amount=Decimal('7000'),
            planned_visit_count=3,
            max_cycle=3,
            service_cycle=1,
        )
        followup = self._job(
            technician=self.tech1,
            partner=self.partner1,
            parent_job=parent,
            service_category=JobCard.ServiceCategory.AMC,
            service_cycle=2,
            max_cycle=3,
            planned_visit_count=3,
            status=JobCard.JobStatus.PENDING,
            is_followup_visit=True,
            included_in_amc=True,
            price='0',
            total_amount=Decimal('0'),
        )

        self._assign(parent, self.tech2)

        followup.refresh_from_db()
        self.assertEqual(followup.technician_id, self.tech2.id)
        self.assertNotIn(followup.id, self._ledger_job_ids(self.tech1))

    def test_heal_command_moves_visits_left_on_previous_technician(self):
        """Bookings reassigned before the fix must be repairable."""
        from django.core.management import call_command

        parent = self._job(technician=self.tech2, partner=self.partner2)
        stale = self._job(
            technician=self.tech1,
            partner=self.partner1,
            parent_job=parent,
            status=JobCard.JobStatus.PENDING,
            is_followup_visit=True,
        )

        call_command('heal_stale_visit_assignments', '--ids', str(parent.id))

        stale.refresh_from_db()
        self.assertEqual(stale.technician_id, self.tech2.id)
        self.assertNotIn(stale.id, self._ledger_job_ids(self.tech1))
        self.assertIn(stale.id, self._ledger_job_ids(self.tech2))
