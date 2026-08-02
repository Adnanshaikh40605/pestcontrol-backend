"""Technician monthly performance (earnings + completed bookings)."""
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Client, JobCard, JobCardTechnicianParticipation, Technician
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianMonthlyPerformanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='perf_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

        self.partner_tech = Technician.objects.create(
            name='Perf Partner',
            mobile='9222000001',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        self.salaried_tech = Technician.objects.create(
            name='Perf Salaried',
            mobile='9222000002',
            technician_type=Technician.TechnicianType.SALARIED,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Perf Partner',
            mobile='9222000001',
            password='x',
            core_technician=self.partner_tech,
            is_app_approved=True,
        )
        self.client_obj = Client.objects.create(
            full_name='Perf Client',
            mobile='9333000001',
        )

    def _done_job(self, technician, price='1000', when=None):
        when = when or timezone.now()
        job = JobCard.objects.create(
            client=self.client_obj,
            technician=technician,
            service_type='Cockroach / Ants',
            job_type='Customer',
            price=price,
            status='Pending',
            schedule_datetime=when,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.APPROVED,
            total_amount=Decimal(price),
            created_by=self.user,
        )
        # Bypass save() auto-now on completed_at for historical month tests
        JobCard.objects.filter(pk=job.pk).update(
            status='Done',
            completed_at=when,
            schedule_datetime=when,
        )
        job.refresh_from_db()
        return job

    def test_monthly_bookings_and_partner_earnings(self):
        now = timezone.now()
        job = self._done_job(self.partner_tech, price='5000', when=now)
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=self.partner_tech,
            partner=self.partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            is_payout_eligible=True,
            payout_amount_snapshot=Decimal('2000.00'),
        )
        PartnerEarning.objects.create(
            partner=self.partner,
            job=job,
            amount=Decimal('2000.00'),
            earning_type=PartnerEarning.EarningType.REVENUE_SHARE,
            is_approved=True,
        )

        res = self.api.get(
            f'/api/v1/technicians/{self.partner_tech.id}/performance_detail/',
            {'year': now.year, 'month': now.month},
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['monthly_bookings'], 1)
        self.assertEqual(Decimal(res.data['monthly_earnings']), Decimal('2000.00'))
        self.assertEqual(res.data['year'], now.year)
        self.assertEqual(res.data['month'], now.month)

    def test_salaried_earnings_are_zero(self):
        now = timezone.now()
        self._done_job(self.salaried_tech, price='3000', when=now)
        res = self.api.get(
            f'/api/v1/technicians/{self.salaried_tech.id}/performance_detail/',
            {'year': now.year, 'month': now.month},
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['monthly_bookings'], 1)
        self.assertEqual(Decimal(res.data['monthly_earnings']), Decimal('0.00'))
        self.assertEqual(res.data['technician_type'], 'salaried')

    def test_previous_month_filter(self):
        now = timezone.now()
        # Job in a fixed past month
        past = timezone.make_aware(datetime(now.year, 1, 15, 12, 0, 0))
        if now.month == 1:
            past = timezone.make_aware(datetime(now.year - 1, 6, 15, 12, 0, 0))
        job = self._done_job(self.partner_tech, price='4000', when=past)
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=self.partner_tech,
            partner=self.partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            payout_amount_snapshot=Decimal('1600.00'),
        )

        res_past = self.api.get(
            f'/api/v1/technicians/{self.partner_tech.id}/performance_detail/',
            {'year': past.year, 'month': past.month},
        )
        self.assertEqual(res_past.status_code, 200, res_past.data)
        self.assertEqual(res_past.data['monthly_bookings'], 1)
        self.assertEqual(Decimal(res_past.data['monthly_earnings']), Decimal('1600.00'))

        res_now = self.api.get(
            f'/api/v1/technicians/{self.partner_tech.id}/performance_detail/',
            {'year': now.year, 'month': now.month},
        )
        self.assertEqual(res_now.status_code, 200, res_now.data)
        self.assertEqual(res_now.data['monthly_bookings'], 0)
        self.assertEqual(Decimal(res_now.data['monthly_earnings']), Decimal('0.00'))
