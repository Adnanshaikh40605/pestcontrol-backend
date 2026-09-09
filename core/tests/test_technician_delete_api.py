"""Permanent technician DELETE API: hard delete with safe cascade/nullify."""
from datetime import date, time
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
    TechnicianRemark,
    TechnicianSettlement,
)
from partner.models import Partner


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianPermanentDeleteApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tech_delete_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

        self.tech = Technician.objects.create(
            name='Delete Me Tech',
            mobile='9111999901',
            is_active=True,
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ACTIVE,
        )
        self.partner = Partner.objects.create(
            full_name='Delete Me Partner',
            mobile='9111999901',
            password='unused',
            core_technician=self.tech,
            is_active=True,
            is_app_approved=True,
        )
        self.client_row = Client.objects.create(
            full_name='Job Client',
            mobile='9111999902',
        )
        self.job = JobCard.objects.create(
            client=self.client_row,
            code=f'DEL-{self.tech.id}',
            status=JobCard.JobStatus.ON_PROCESS,
            technician=self.tech,
            partner=self.partner,
            assigned_to=self.tech.name,
            schedule_datetime=timezone.now(),
        )
        self.participation = JobCardTechnicianParticipation.objects.create(
            jobcard=self.job,
            technician=self.tech,
            partner=self.partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
        )
        self.remark = TechnicianRemark.objects.create(
            technician=self.tech,
            remark='Will be removed with technician',
            remark_date=date.today(),
            remark_time=time(10, 0),
            created_by=self.user,
        )
        self.settlement = TechnicianSettlement.objects.create(
            technician=self.tech,
            partner=self.partner,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 7),
            cadence=TechnicianSettlement.Cadence.WEEKLY,
            status=TechnicianSettlement.Status.PAID,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('1000.00'),
        )

    def test_delete_requires_authentication(self):
        anon = APIClient()
        res = anon.delete(f'/api/v1/technicians/{self.tech.id}/')
        self.assertIn(res.status_code, (401, 403))

    def test_permanent_delete_removes_technician_and_cascades_safely(self):
        tech_id = self.tech.id
        job_id = self.job.id
        settlement_id = self.settlement.id
        partner_id = self.partner.id
        remark_id = self.remark.id
        participation_id = self.participation.id

        res = self.api.delete(f'/api/v1/technicians/{tech_id}/')
        self.assertEqual(res.status_code, 204, getattr(res, 'data', res.content))

        self.assertFalse(Technician.objects.filter(id=tech_id).exists())
        self.assertFalse(TechnicianRemark.objects.filter(id=remark_id).exists())
        self.assertFalse(
            JobCardTechnicianParticipation.objects.filter(id=participation_id).exists()
        )

        job = JobCard.objects.get(id=job_id)
        self.assertIsNone(job.technician_id)
        self.assertIsNone(job.assigned_to)
        # Partner FK on bookings is kept for audit; the Partner row is deactivated.
        self.assertEqual(job.partner_id, partner_id)

        settlement = TechnicianSettlement.objects.get(id=settlement_id)
        self.assertIsNone(settlement.technician_id)
        self.assertEqual(settlement.net_amount, Decimal('1000.00'))

        partner = Partner.objects.get(id=partner_id)
        self.assertIsNone(partner.core_technician_id)
        self.assertFalse(partner.is_app_approved)
        self.assertFalse(partner.is_active)

        list_res = self.api.get('/api/v1/technicians/', {'search': 'Delete Me Tech'})
        self.assertEqual(list_res.status_code, 200)
        ids = [row['id'] for row in list_res.data.get('results', list_res.data)]
        self.assertNotIn(tech_id, ids)
