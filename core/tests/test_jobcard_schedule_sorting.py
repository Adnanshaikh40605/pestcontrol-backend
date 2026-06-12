"""Tests for JobCard booking date/time sorting."""
from datetime import datetime

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

        self.samples = [
            ('13/10/2025 12:15 PM', datetime(2025, 10, 13), '12:15 PM'),
            ('21/11/2025 12:30 PM', datetime(2025, 11, 21), '12:30 PM'),
            ('23/11/2025 02:00 PM', datetime(2025, 11, 23), '02:00 PM'),
            ('15/06/2026 01:00 PM', datetime(2026, 6, 15), '01:00 PM'),
            ('17/06/2026 10:00 AM', datetime(2026, 6, 17), '10:00 AM'),
            ('21/06/2026 12:00 PM', datetime(2026, 6, 21), '12:00 PM'),
        ]

    def _create_booking(self, day: datetime, time_slot: str) -> JobCard:
        naive_midnight = IST.localize(datetime(day.year, day.month, day.day, 0, 0, 0))
        return JobCard.objects.create(
            client=self.customer,
            service_type='General Pest Control',
            status=JobCard.JobStatus.PENDING,
            schedule_datetime=naive_midnight.astimezone(timezone.utc),
            time_slot=time_slot,
        )

    def test_queryset_order_ascending_and_descending(self):
        created = [self._create_booking(day, slot) for _, day, slot in self.samples]
        asc_ids = list(
            order_queryset_by_schedule_datetime(
                JobCard.objects.filter(id__in=[j.id for j in created]),
                ascending=True,
            ).values_list('id', flat=True)
        )
        desc_ids = list(
            order_queryset_by_schedule_datetime(
                JobCard.objects.filter(id__in=[j.id for j in created]),
                ascending=False,
            ).values_list('id', flat=True)
        )
        self.assertEqual(asc_ids, [j.id for j in created])
        self.assertEqual(desc_ids, list(reversed(asc_ids)))

    def test_api_pending_tab_sorts_chronologically_by_default(self):
        created = []
        for _, day, slot in self.samples:
            created.append(self._create_booking(day, slot))

        response = self.api_client.get(
            '/api/v1/jobcards/',
            {
                'booking_type': 'pending',
                'page_size': 20,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [row['id'] for row in response.data['results']]
        self.assertEqual(result_ids, [job.id for job in created])

    def test_api_booking_tabs_ignore_manual_desc_ordering(self):
        created = []
        for _, day, slot in self.samples:
            created.append(self._create_booking(day, slot))

        for booking_type in (
            'pending',
            'on_process',
            'done',
            'upcoming_services',
            'complaint_calls',
            'cancelled',
        ):
            JobCard.objects.filter(id__in=[job.id for job in created]).update(
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
                JobCard.objects.filter(id__in=[job.id for job in created]).update(
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
                [job.id for job in created],
                msg=f'{booking_type} should always sort nearest schedule first',
            )

    def test_api_sorting_stable_with_pagination(self):
        """Default API page size is 10 — verify sort order is consistent across pages."""
        extra_days = [
            datetime(2026, 6, 22),
            datetime(2026, 6, 23),
            datetime(2026, 6, 24),
            datetime(2026, 6, 25),
            datetime(2026, 6, 26),
        ]
        for _, day, slot in self.samples:
            self._create_booking(day, slot)
        for day in extra_days:
            self._create_booking(day, '09:00 AM')

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
        self.assertEqual(len(page2.data['results']), 1)
        page1_times = [row['schedule_datetime'] for row in page1.data['results']]
        self.assertEqual(page1_times, sorted(page1_times))
        self.assertGreater(page2.data['results'][0]['schedule_datetime'], page1_times[-1])
