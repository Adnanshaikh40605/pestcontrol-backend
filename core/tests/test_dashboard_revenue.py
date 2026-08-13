from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import Client, JobCard
from core.services import DashboardService


class DashboardRevenueByServiceDateTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(full_name='Hist Client', mobile='9000000001')
        self.today = timezone.now().date()
        self.month_start = self.today.replace(day=1)
        self.last_month_day = self.month_start - timedelta(days=15)

        self.current_month_schedule = timezone.make_aware(
            datetime.combine(self.today, datetime.min.time())
        )
        self.last_month_schedule = timezone.make_aware(
            datetime.combine(self.last_month_day, datetime.min.time())
        )

    def _done_job(self, *, schedule, price, completed=None):
        return JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=schedule,
            price=str(price),
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=completed or timezone.now(),
        )

    def test_backfilled_last_month_booking_does_not_count_in_current_month_revenue(self):
        """Historical service entered/marked done today must not inflate this month."""
        self._done_job(
            schedule=self.last_month_schedule,
            price=5000,
            completed=timezone.now(),
        )

        stats = DashboardService.get_dashboard_statistics()
        self.assertEqual(stats['month_revenue'], 0)

    def test_current_month_service_date_counts_in_month_revenue(self):
        self._done_job(
            schedule=self.current_month_schedule,
            price=3000,
            completed=timezone.now(),
        )

        stats = DashboardService.get_dashboard_statistics()
        self.assertEqual(stats['month_revenue'], 3000)

    def test_range_revenue_uses_service_date(self):
        self._done_job(
            schedule=self.last_month_schedule,
            price=2000,
            completed=timezone.now(),
        )
        self._done_job(
            schedule=self.current_month_schedule,
            price=4000,
            completed=timezone.now(),
        )

        stats = DashboardService.get_dashboard_statistics(
            from_date=self.today.isoformat(),
            to_date=self.today.isoformat(),
        )
        self.assertEqual(stats['range_revenue'], 4000)
        self.assertEqual(stats['today_revenue'], 4000)

    def test_last_month_revenue_uses_service_date(self):
        self._done_job(
            schedule=self.last_month_schedule,
            price=2500,
            completed=timezone.now(),
        )

        stats = DashboardService.get_dashboard_statistics()
        self.assertEqual(stats['last_month_revenue'], 2500)


class DashboardTodayCitySplitTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(full_name='City Client', mobile='9000000099')
        self.today = timezone.make_aware(datetime.combine(timezone.now().date(), datetime.min.time()))

    def test_today_bookings_and_service_calls_split_by_city(self):
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            city='Mumbai',
            schedule_datetime=self.today,
            price='1000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            is_service_call=False,
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            city='Mumbai',
            schedule_datetime=self.today,
            price='0',
            reference='Other',
            status=JobCard.JobStatus.UPCOMING,
            booking_type=JobCard.BookingType.SERVICE_CALL,
            booking_category=JobCard.BookingCategory.SERVICE_CALL,
            is_service_call=True,
            service_cycle=2,
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            city='Pune',
            schedule_datetime=self.today,
            price='0',
            reference='Other',
            status=JobCard.JobStatus.UPCOMING,
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
            booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
            is_service_call=True,
            service_cycle=2,
        )

        stats = DashboardService.get_dashboard_statistics()
        self.assertEqual(stats['today_booking_count'], 1)
        self.assertEqual(stats['today_service_call_count'], 2)
        self.assertEqual(stats['today_city_stats'], [{'city': 'Mumbai', 'count': 1}])
        service_by_city = {row['city']: row['count'] for row in stats['today_service_city_stats']}
        self.assertEqual(service_by_city.get('Mumbai'), 1)
        self.assertEqual(service_by_city.get('Pune'), 1)
