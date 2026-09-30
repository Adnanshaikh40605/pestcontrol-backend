"""Daily technician type report (performing / non-performing + city earnings)."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Client, JobCard, JobCardTechnicianParticipation, Technician
from partner.models import Partner


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianDailyTypeReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='daily_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

        self.today = timezone.localtime()
        self.partner_tech = Technician.objects.create(
            name='Daily Partner',
            mobile='9444000001',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
            city='Mumbai',
        )
        self.idle_partner = Technician.objects.create(
            name='Idle Partner',
            mobile='9444000002',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
            city='Pune',
        )
        self.secondary_tech = Technician.objects.create(
            name='Daily Secondary',
            mobile='9444000003',
            technician_type=Technician.TechnicianType.SECONDARY,
            is_active=True,
            city='Mumbai',
        )
        self.partner = Partner.objects.create(
            full_name='Daily Partner',
            mobile='9444000001',
            password='x',
            core_technician=self.partner_tech,
            is_app_approved=True,
        )
        self.client_obj = Client.objects.create(
            full_name='Daily Client',
            mobile='9555000001',
        )

    def _done_job(self, technician, *, price='1000', service='Cockroach / Ants', city='Mumbai'):
        job = JobCard.objects.create(
            client=self.client_obj,
            technician=technician,
            service_type=service,
            job_type='Customer',
            price=price,
            status='Pending',
            schedule_datetime=self.today,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.APPROVED,
            total_amount=Decimal(price),
            city=city,
            visit_payout_amount=Decimal(price) * Decimal('0.40'),
            created_by=self.user,
        )
        JobCard.objects.filter(pk=job.pk).update(
            status='Done',
            completed_at=self.today,
            schedule_datetime=self.today,
        )
        job.refresh_from_db()
        return job

    def test_priority_alias_and_performing_split(self):
        job = self._done_job(self.partner_tech, price='5000', service='Termite Control')
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=self.partner_tech,
            partner=self.partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            is_payout_eligible=True,
            payout_amount_snapshot=Decimal('2000.00'),
        )

        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'priority',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['technician_type'], 'partner')
        self.assertIn('Priority', res.data['technician_type_label'])
        self.assertEqual(res.data['summary']['performing_count'], 1)
        self.assertEqual(res.data['summary']['non_performing_count'], 1)
        self.assertEqual(len(res.data['performing']), 1)
        self.assertEqual(res.data['performing'][0]['name'], 'Daily Partner')
        self.assertEqual(res.data['performing'][0]['completed_count'], 1)
        self.assertTrue(
            any('Termite' in s['service_type'] for s in res.data['performing'][0]['services'])
        )
        self.assertEqual(res.data['non_performing'][0]['name'], 'Idle Partner')
        self.assertTrue(len(res.data['city_earnings']) >= 1)
        mumbai = next(c for c in res.data['city_earnings'] if c['city'] == 'Mumbai')
        self.assertEqual(mumbai['completed_jobs'], 1)

    def test_secondary_report_isolated(self):
        self._done_job(self.secondary_tech, price='3000', city='Mumbai')
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'secondary',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['summary']['performing_count'], 1)
        self.assertEqual(res.data['performing'][0]['name'], 'Daily Secondary')

    def test_invalid_type_rejected(self):
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {'technician_type': 'unknown'},
        )
        self.assertEqual(res.status_code, 400)

    def test_yesterday_empty_for_today_jobs(self):
        self._done_job(self.partner_tech, price='2000')
        yesterday = (self.today - timedelta(days=1)).date().isoformat()
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {'date': yesterday, 'technician_type': 'partner'},
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['summary']['performing_count'], 0)
        self.assertEqual(res.data['summary']['non_performing_count'], 2)

    def test_absent_crew_not_counted_as_performing(self):
        """Crew rows without completed attendance must not mark a tech performing."""
        job = self._done_job(self.partner_tech, price='4000', city='Mumbai')
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=self.idle_partner,
            role=JobCardTechnicianParticipation.Role.CREW,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.ABSENT,
            is_payout_eligible=False,
            payout_amount_snapshot=Decimal('0.00'),
        )
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'priority',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        performing_names = {r['name'] for r in res.data['performing']}
        self.assertIn('Daily Partner', performing_names)
        self.assertNotIn('Idle Partner', performing_names)
        self.assertEqual(res.data['summary']['performing_count'], 1)

    def test_bad_date_rejected(self):
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {'date': 'not-a-date', 'technician_type': 'partner'},
        )
        self.assertEqual(res.status_code, 400)

    def test_cancelled_visit_is_not_performing(self):
        job = self._done_job(self.partner_tech, price='2000', service='Bed Bugs')
        JobCard.objects.filter(pk=job.pk).update(status=JobCard.JobStatus.CANCELLED)
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'priority',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['summary']['performing_count'], 0)
        self.assertEqual(res.data['summary']['total_completed_jobs'], 0)
        self.assertEqual(res.data['summary']['non_performing_count'], 2)

    def test_service_type_counts_and_city_earnings(self):
        self._done_job(self.partner_tech, price='1000', service='Cockroach Standard', city='Mumbai')
        self._done_job(self.partner_tech, price='1000', service='Cockroach Standard', city='Mumbai')
        self._done_job(self.partner_tech, price='1500', service='Bed Bugs', city='Pune')
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'partner',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        row = res.data['performing'][0]
        self.assertEqual(row['completed_count'], 3)
        by_type = {s['service_type']: s['count'] for s in row['services']}
        self.assertEqual(by_type.get('Cockroach Standard'), 2)
        self.assertEqual(by_type.get('Bed Bugs'), 1)
        self.assertIn('Cockroach Standard 2', row['services_summary'])
        self.assertIn('Bed Bugs 1', row['services_summary'])
        cities = {c['city']: c for c in row['city_earnings']}
        self.assertEqual(cities['Mumbai']['completed_jobs'], 2)
        self.assertEqual(cities['Pune']['completed_jobs'], 1)
        rollup = {c['city']: c['completed_jobs'] for c in res.data['city_earnings']}
        self.assertEqual(rollup['Mumbai'], 2)
        self.assertEqual(rollup['Pune'], 1)

    def test_stored_base_share_is_not_gst_peeled(self):
        """1600 is already the ex-GST base. A stored 30% split stays 480, not 480/1.18 or 40%."""
        job = self._done_job(
            self.partner_tech,
            price='1600.00',
            service='Cockroach Standard',
            city='Mumbai',
        )
        JobCard.objects.filter(pk=job.pk).update(
            price='1600.00',
            total_amount=Decimal('1600.00'),
            visit_revenue_amount=Decimal('1600.00'),
            visit_payout_amount=Decimal('480.00'),
            technician_pool_amount=Decimal('480.00'),
            company_share_amount=Decimal('1120.00'),
            technician_share_percent=Decimal('30.00'),
            company_share_percent=Decimal('70.00'),
            service_items=[{
                'service': 'Cockroach Standard',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'amount': 1600.0,
                'base_amount': 1600.0,
            }],
        )
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=self.partner_tech,
            partner=self.partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            is_payout_eligible=True,
            payout_amount_snapshot=Decimal('480.00'),
            share_percent_snapshot=Decimal('30.00'),
        )
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'priority',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        row = res.data['performing'][0]
        self.assertEqual(Decimal(row['earnings']), Decimal('480.00'))
        self.assertNotEqual(Decimal(row['earnings']), Decimal('406.78'))
        self.assertNotEqual(Decimal(row['earnings']), Decimal('640.00'))
        mumbai = next(c for c in row['city_earnings'] if c['city'] == 'Mumbai')
        self.assertEqual(Decimal(mumbai['earnings']), Decimal('480.00'))

    def test_salaried_completion_earns_nothing(self):
        salaried = Technician.objects.create(
            name='Daily Salaried',
            mobile='9444000004',
            technician_type=Technician.TechnicianType.SALARIED,
            is_active=True,
            city='Mumbai',
        )
        self._done_job(salaried, price='2000', service='Bed Bugs', city='Mumbai')
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'salaried',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['summary']['performing_count'], 1)
        self.assertEqual(Decimal(res.data['performing'][0]['earnings']), Decimal('0.00'))
        self.assertEqual(Decimal(res.data['summary']['total_earnings']), Decimal('0.00'))

    def test_inactive_technician_is_omitted(self):
        Technician.objects.create(
            name='Left Partner',
            mobile='9444000005',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=False,
            city='Mumbai',
        )
        res = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {
                'date': self.today.date().isoformat(),
                'technician_type': 'priority',
            },
        )
        self.assertEqual(res.status_code, 200, res.data)
        names = {r['name'] for r in res.data['performing'] + res.data['non_performing']}
        self.assertNotIn('Left Partner', names)
        self.assertEqual(res.data['summary']['total_technicians'], 2)

    def test_kolkata_midnight_belongs_to_that_india_date(self):
        ist = ZoneInfo('Asia/Kolkata')
        stamp = datetime(2026, 9, 28, 0, 30, tzinfo=ist)
        job = self._done_job(self.partner_tech, price='1000', service='Bed Bugs')
        JobCard.objects.filter(pk=job.pk).update(
            completed_at=stamp,
            schedule_datetime=stamp,
        )
        on_the_day = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {'date': '2026-09-28', 'technician_type': 'partner'},
        )
        previous = self.api.get(
            '/api/v1/technicians/daily_type_report/',
            {'date': '2026-09-27', 'technician_type': 'partner'},
        )
        self.assertEqual(on_the_day.status_code, 200, on_the_day.data)
        self.assertEqual(previous.status_code, 200, previous.data)
        self.assertEqual(on_the_day.data['summary']['performing_count'], 1)
        self.assertEqual(on_the_day.data['performing'][0]['name'], 'Daily Partner')
        self.assertEqual(previous.data['summary']['performing_count'], 0)
