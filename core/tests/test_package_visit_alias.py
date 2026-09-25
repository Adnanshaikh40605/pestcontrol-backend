"""Renamed service lines must not spawn a second visit, and one shell lead wins."""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.booking_schedule_engine import (
    BookingScheduleEngine,
    align_uniform_day1_technicians_to_shell,
    retire_duplicate_package_visits,
    service_cycle_already_exists,
)
from core.models import Client, JobCard, JobCardTechnicianParticipation, Technician


class PackageVisitAliasTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(full_name='Jithu', mobile='9656311133')
        self.sohil = Technician.objects.create(
            name='Sohil',
            mobile='9000002201',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        self.manjeet = Technician.objects.create(
            name='Manjeet',
            mobile='9000002202',
            technician_type=Technician.TechnicianType.PARTNER,
        )

    def _shell(self, technician):
        return JobCard.objects.create(
            client=self.client_obj,
            service_type='Cockroach Standard, Bed Bugs',
            service_items=[
                {
                    'service': 'Cockroach Standard',
                    'plan': 'AMC 3 Services',
                    'area': '1 BHK',
                    'amount': 2100,
                    'base_amount': 2100,
                },
                {
                    'service': 'Bed Bugs',
                    'plan': 'One Time Service',
                    'area': '1 BHK',
                    'amount': 2400,
                    'base_amount': 2400,
                },
            ],
            schedule_datetime=datetime(2026, 9, 9, 8, 30, tzinfo=dt_timezone.utc),
            price='4500',
            technician=technician,
            assigned_to=technician.name,
            status=JobCard.JobStatus.DONE,
            completed_at=timezone.now(),
            reference='Website',
            client_address='Chunabhatti',
            visit_type='MULTI SERVICE PACKAGE',
        )

    def _child(self, shell, *, service, cycle, technician, status, source=None):
        return JobCard.objects.create(
            client=self.client_obj,
            parent_job=shell,
            service_type=service,
            source_service=source or service,
            service_items=[{'service': service, 'plan': 'AMC 3 Services', 'area': '1 BHK', 'amount': 2100}],
            service_cycle=cycle,
            max_cycle=3,
            schedule_datetime=shell.schedule_datetime,
            price='2100' if cycle == 1 else '0',
            technician=technician,
            assigned_to=technician.name if technician else '',
            status=status,
            is_auto_generated=True,
            reference='Website',
        )

    def test_renamed_cockroach_line_is_the_same_visit(self):
        shell = self._shell(self.manjeet)
        self._child(
            shell,
            service='Cockroach / Ants',
            cycle=1,
            technician=self.sohil,
            status=JobCard.JobStatus.DONE,
        )
        self.assertTrue(service_cycle_already_exists(shell, 'Cockroach Standard', 1))
        created = BookingScheduleEngine.backfill_missing_day1_children(shell)
        names = [c.service_type for c in created]
        self.assertNotIn('Cockroach Standard', names)
        self.assertEqual(
            JobCard.objects.filter(parent_job=shell, service_cycle=1, status=JobCard.JobStatus.CANCELLED).count(),
            0,
        )

    def test_duplicate_pending_line_is_cancelled(self):
        shell = self._shell(self.manjeet)
        done = self._child(
            shell,
            service='Cockroach / Ants',
            cycle=1,
            technician=self.sohil,
            status=JobCard.JobStatus.DONE,
        )
        done.visit_revenue_amount = Decimal('700.00')
        done.save(update_fields=['visit_revenue_amount'])
        duplicate = self._child(
            shell,
            service='Cockroach Standard',
            cycle=1,
            technician=self.manjeet,
            status=JobCard.JobStatus.PENDING,
        )
        blob = self._child(
            shell,
            service='Multiple Pests: Cockroach / Ants, Bed Bugs',
            source='Multiple Pests: Cockroach / Ants, Bed Bugs',
            cycle=2,
            technician=None,
            status=JobCard.JobStatus.UPCOMING,
        )
        retired = retire_duplicate_package_visits(shell)
        duplicate.refresh_from_db()
        blob.refresh_from_db()
        done.refresh_from_db()
        self.assertEqual(duplicate.status, JobCard.JobStatus.CANCELLED)
        self.assertTrue(duplicate.hidden_from_technician_ledger)
        self.assertEqual(blob.status, JobCard.JobStatus.CANCELLED)
        self.assertEqual(done.status, JobCard.JobStatus.DONE)
        self.assertIn(duplicate.id, [r.id for r in retired])

    def test_shell_reassignment_moves_uniform_day1_visits(self):
        shell = self._shell(self.manjeet)
        cockroach = self._child(
            shell, service='Cockroach / Ants', cycle=1,
            technician=self.sohil, status=JobCard.JobStatus.DONE,
        )
        bed = self._child(
            shell, service='Bed Bugs', cycle=1,
            technician=self.sohil, status=JobCard.JobStatus.DONE,
        )
        older = timezone.now() - timezone.timedelta(hours=2)
        newer = timezone.now()
        for child in (cockroach, bed):
            row = JobCardTechnicianParticipation.objects.create(
                jobcard=child,
                technician=self.sohil,
                role=JobCardTechnicianParticipation.Role.LEAD,
            )
            JobCardTechnicianParticipation.objects.filter(pk=row.pk).update(created_at=older)
        shell_row = JobCardTechnicianParticipation.objects.create(
            jobcard=shell,
            technician=self.manjeet,
            role=JobCardTechnicianParticipation.Role.LEAD,
        )
        JobCardTechnicianParticipation.objects.filter(pk=shell_row.pk).update(created_at=newer)

        moved = align_uniform_day1_technicians_to_shell(shell)
        cockroach.refresh_from_db()
        bed.refresh_from_db()
        self.assertEqual(len(moved), 2)
        self.assertEqual(cockroach.technician_id, self.manjeet.id)
        self.assertEqual(bed.technician_id, self.manjeet.id)

    def test_different_service_technicians_are_not_overwritten(self):
        shell = self._shell(self.manjeet)
        cockroach = self._child(
            shell, service='Cockroach / Ants', cycle=1,
            technician=self.sohil, status=JobCard.JobStatus.DONE,
        )
        bed = self._child(
            shell, service='Bed Bugs', cycle=1,
            technician=self.manjeet, status=JobCard.JobStatus.DONE,
        )
        JobCardTechnicianParticipation.objects.create(
            jobcard=shell, technician=self.manjeet,
            role=JobCardTechnicianParticipation.Role.LEAD,
        )
        moved = align_uniform_day1_technicians_to_shell(shell)
        cockroach.refresh_from_db()
        self.assertEqual(moved, [])
        self.assertEqual(cockroach.technician_id, self.sohil.id)
        self.assertEqual(bed.technician_id, self.manjeet.id)
