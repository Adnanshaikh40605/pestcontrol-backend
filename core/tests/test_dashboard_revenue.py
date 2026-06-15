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
