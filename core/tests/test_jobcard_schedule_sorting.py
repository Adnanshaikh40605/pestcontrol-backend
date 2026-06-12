"""Tests for JobCard booking date/time sorting."""
from datetime import datetime, timedelta

import pytz
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.jobcard_schedule import effective_schedule_datetime, order_queryset_by_schedule_datetime
from core.models import Client, JobCard

IST = pytz.timezone('Asia/Kolkata')


class JobCardScheduleUtilsTest(APITestCase):
    def test_effective_schedule_datetime_merges_time_slot(self):
        base = IST.localize(datetime(2025, 10, 13, 0, 0, 0)).astimezone(timezone.utc)
        merged = effective_schedule_datetime(base, '12:15 PM')
        local = merged.astimezone(IST)
        self.assertEqual(local.year, 2025)
        self.assertEqual(local.month, 10)
        self.assertEqual(local.day, 13)
        self.assertEqual(local.hour, 12)
        self.assertEqual(local.minute, 15)

    def test_effective_schedule_datetime_keeps_explicit_time_without_slot(self):
        base = IST.localize(datetime(2026, 6, 17, 10, 0, 0)).astimezone(timezone.utc)
        merged = effective_schedule_datetime(base, None)
        local = merged.astimezone(IST)
        self.assertEqual(local.hour, 10)
        self.assertEqual(local.minute, 0)


class JobCardScheduleSortingAPITest(APITestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.user = User.objects.create_superuser(
            username='sorttest',
            email='sort@test.com',
            password='testpass123',
        )
        refresh = RefreshToken.for_user(self.user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.customer = Client.objects.create(
            full_name='Sort Test Client',
            mobile='9000000001',
            city='Lonavala',
        )

        self.today = timezone.now().astimezone(IST).date()
        self.tomorrow = self.today + timedelta(days=1)
        self.future = self.today + timedelta(days=5)
        self.past = self.today - timedelta(days=120)

    def _create_booking(self, day, time_slot: str, **kwargs) -> JobCard:
        naive_midnight = IST.localize(datetime(day.year, day.month, day.day, 0, 0, 0))
        return JobCard.objects.create(
            client=self.customer,
            service_type='General Pest Control',
            status=kwargs.pop('status', JobCard.JobStatus.PENDING),
            schedule_datetime=naive_midnight.astimezone(timezone.utc),
            time_slot=time_slot,
            **kwargs,
        )

    def test_queryset_prioritizes_today_before_past_and_future(self):
        past_job = self._create_booking(self.past, '10:00 AM')
        today_morning = self._create_booking(self.today, '10:00 AM')
        today_evening = self._create_booking(self.today, '08:30 PM')
        tomorrow_job = self._create_booking(self.tomorrow, '12:00 PM')
        future_job = self._create_booking(self.future, '01:00 PM')

        ordered_ids = list(
            order_queryset_by_schedule_datetime(
                JobCard.objects.filter(
                    id__in=[
                        past_job.id,
                        today_morning.id,
                        today_evening.id,
                        tomorrow_job.id,
                        future_job.id,
                    ]
                ),
                ascending=True,
            ).values_list('id', flat=True)
        )

        self.assertEqual(
            ordered_ids,
            [today_morning.id, today_evening.id, tomorrow_job.id, future_job.id, past_job.id],
        )

    def test_api_pending_tab_puts_today_on_page_one_before_past(self):
        past_job = self._create_booking(self.past, '12:15 PM')
        today_job = self._create_booking(self.today, '08:30 PM')
        tomorrow_job = self._create_booking(self.tomorrow, '12:00 PM')
        future_job = self._create_booking(self.future, '01:00 PM')

        response = self.api_client.get(
            '/api/v1/jobcards/',
            {
                'booking_type': 'pending',
                'page_size': 3,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [row['id'] for row in response.data['results']]
        self.assertEqual(result_ids, [today_job.id, tomorrow_job.id, future_job.id])
        self.assertNotIn(past_job.id, result_ids)

        page2 = self.api_client.get(
            '/api/v1/jobcards/',
            {'booking_type': 'pending', 'page': 2, 'page_size': 3},
        )
        self.assertEqual(page2.status_code, status.HTTP_200_OK)
        self.assertEqual(page2.data['results'][0]['id'], past_job.id)

    def test_api_booking_tabs_ignore_manual_desc_ordering(self):
        jobs = [
            self._create_booking(self.past, '10:00 AM'),
            self._create_booking(self.today, '02:00 PM'),
            self._create_booking(self.tomorrow, '09:00 AM'),
            self._create_booking(self.future, '11:00 AM'),
        ]
        expected_order = [jobs[1].id, jobs[2].id, jobs[3].id, jobs[0].id]

        for booking_type in (
            'pending',
            'on_process',
            'done',
            'upcoming_services',
            'complaint_calls',
            'cancelled',
        ):
            JobCard.objects.filter(id__in=[job.id for job in jobs]).update(
                status={
                    'pending': JobCard.JobStatus.PENDING,
                    'on_process': JobCard.JobStatus.ON_PROCESS,
                    'done': JobCard.JobStatus.DONE,
                    'upcoming_services': JobCard.JobStatus.UPCOMING,
                    'complaint_calls': JobCard.JobStatus.PENDING,
                    'cancelled': JobCard.JobStatus.CANCELLED,
                }[booking_type],
                booking_category=(
                    JobCard.BookingCategory.COMPLAINT_CALL
                    if booking_type == 'complaint_calls'
                    else JobCard.BookingCategory.NORMAL_BOOKING
                ),
            )
            if booking_type == 'upcoming_services':
                JobCard.objects.filter(id__in=[job.id for job in jobs]).update(
                    booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
                )

            response = self.api_client.get(
                '/api/v1/jobcards/',
                {
                    'booking_type': booking_type,
                    'ordering': '-schedule_datetime',
                    'page_size': 20,
                },
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            result_ids = [row['id'] for row in response.data['results']]
            self.assertEqual(
                result_ids,
                expected_order,
                msg=f'{booking_type} should always sort today → tomorrow → future → past',
            )

    def test_api_sorting_stable_with_pagination(self):
        """Page 1 must contain today/tomorrow before overdue past bookings."""
        self._create_booking(self.past, '09:00 AM')
        self._create_booking(self.past - timedelta(days=30), '09:00 AM')
        self._create_booking(self.past - timedelta(days=60), '09:00 AM')
        self._create_booking(self.past - timedelta(days=90), '09:00 AM')
        self._create_booking(self.past - timedelta(days=120), '09:00 AM')
        self._create_booking(self.past - timedelta(days=150), '09:00 AM')
        self._create_booking(self.past - timedelta(days=180), '09:00 AM')
        today_job = self._create_booking(self.today, '08:30 PM')
        tomorrow_job = self._create_booking(self.tomorrow, '12:00 PM')
        for offset in range(1, 5):
            self._create_booking(self.future + timedelta(days=offset), '09:00 AM')

        page1 = self.api_client.get(
            '/api/v1/jobcards/',
            {'booking_type': 'pending', 'page': 1},
        )
        page2 = self.api_client.get(
            '/api/v1/jobcards/',
            {'booking_type': 'pending', 'page': 2},
        )
        self.assertEqual(page1.status_code, status.HTTP_200_OK)
        self.assertEqual(page2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(page1.data['results']), 10)
        page1_ids = [row['id'] for row in page1.data['results']]
        self.assertEqual(page1_ids[0], today_job.id)
        self.assertEqual(page1_ids[1], tomorrow_job.id)
        self.assertGreater(len(page2.data['results']), 0)
