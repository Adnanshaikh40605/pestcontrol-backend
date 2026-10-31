"""Today's technician report lists only today's active assignments."""

from datetime import datetime, timedelta

import pytz
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Client, JobCard, Technician

IST = pytz.timezone('Asia/Kolkata')


class TodayTechnicianReportTests(APITestCase):
    def setUp(self):
        self.api = APIClient()
        user = User.objects.create_superuser(
            username='todayreport',
            email='todayreport@test.com',
            password='testpass123',
        )
        refresh = RefreshToken.for_user(user)
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.customer = Client.objects.create(
            full_name='Nandlal',
            mobile='9421191834',
            city='Pune',
        )
        self.today = timezone.now().astimezone(IST).date()
        self.active = Technician.objects.create(
            name='Salman Shaikh',
            mobile='9000011111',
            is_active=True,
        )
        self.inactive = Technician.objects.create(
            name='Inactive Tech',
            mobile='9000022222',
            is_active=False,
        )

    def _booking(self, day, technician, **kwargs):
        stamp = IST.localize(datetime(day.year, day.month, day.day, 11, 0, 0))
        return JobCard.objects.create(
            client=self.customer,
            service_type=kwargs.pop('service_type', 'Bed Bugs'),
            status=kwargs.pop('status', JobCard.JobStatus.ON_PROCESS),
            schedule_datetime=stamp.astimezone(timezone.utc),
            time_slot=kwargs.pop('time_slot', '11:00 AM'),
            price=kwargs.pop('price', '2500'),
            city=kwargs.pop('city', 'Pune'),
            technician=technician,
            assigned_to=technician.name if technician else '',
            **kwargs,
        )

    def test_groups_today_jobs_for_active_technicians_only(self):
        today_job = self._booking(self.today, self.active)
        second = self._booking(
            self.today,
            self.active,
            service_type='Cockroach Standard',
            price='1180',
            city='Thane',
            status=JobCard.JobStatus.PENDING,
        )
        self._booking(self.today + timedelta(days=1), self.active)
        self._booking(self.today, self.inactive)
        self._booking(self.today, None, status=JobCard.JobStatus.PENDING)
        self._booking(
            self.today,
            self.active,
            status=JobCard.JobStatus.CANCELLED,
        )

        response = self.api.get('/api/v1/jobcards/today-technician-report/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['date'], self.today.isoformat())
        self.assertEqual(response.data['technician_count'], 1)
        self.assertEqual(response.data['booking_count'], 2)

        tech = response.data['technicians'][0]
        self.assertEqual(tech['name'], 'Salman Shaikh')
        self.assertEqual(tech['mobile'], '9000011111')
        self.assertEqual(tech['booking_count'], 2)
        self.assertEqual(tech['locations'], ['Pune', 'Thane'])
        ids = [row['id'] for row in tech['jobs']]
        self.assertEqual(ids, [today_job.id, second.id])
        first = tech['jobs'][0]
        self.assertEqual(first['customer_name'], 'Nandlal')
        self.assertEqual(first['customer_mobile'], '9421191834')
        self.assertEqual(first['service_type'], 'Bed Bugs')
        self.assertEqual(first['price_label'], '₹2,500')
        self.assertEqual(first['location'], 'Pune')
        self.assertEqual(first['status'], 'On Process')
        self.assertEqual(first['time_slot'], '11:00 AM')
