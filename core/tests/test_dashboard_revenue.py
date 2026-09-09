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

    def test_month_revenue_excludes_service_call_amounts(self):
        """Monthly Target counts only new/initial bookings — not Service Calls."""
        self._done_job(
            schedule=self.current_month_schedule,
            price=5000,
            completed=timezone.now(),
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.current_month_schedule,
            price='2000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.SERVICE_CALL,
            booking_category=JobCard.BookingCategory.SERVICE_CALL,
            is_service_call=True,
            service_cycle=2,
            completed_at=timezone.now(),
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.current_month_schedule,
            price='1500',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
            booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
            is_service_call=True,
            service_cycle=2,
            completed_at=timezone.now(),
        )

        stats = DashboardService.get_dashboard_statistics()
        self.assertEqual(stats['month_revenue'], 5000)
        self.assertEqual(stats['today_revenue'], 5000)
        self.assertAlmostEqual(stats['month_achievement_pct'], 1.0)  # 5000/500000*100

    def test_amc_main_counts_in_month_revenue_but_followup_does_not(self):
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.current_month_schedule,
            price='8000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.AMC_MAIN,
            booking_category=JobCard.BookingCategory.NORMAL_BOOKING,
            is_service_call=False,
            completed_at=timezone.now(),
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.current_month_schedule,
            price='0',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
            booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
            is_service_call=True,
            service_cycle=2,
            completed_at=timezone.now(),
        )
        stats = DashboardService.get_dashboard_statistics()
        self.assertEqual(stats['month_revenue'], 8000)


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
        self.assertEqual(stats['today_complaint_call_count'], 0)
        self.assertEqual(stats['today_city_stats'], [{'city': 'Mumbai', 'count': 1}])
        service_by_city = {row['city']: row['count'] for row in stats['today_service_city_stats']}
        self.assertEqual(service_by_city.get('Mumbai'), 1)
        self.assertEqual(service_by_city.get('Pune'), 1)
        # Selected date range uses the same booking / service city split.
        self.assertEqual(stats['range_booking_count'], 1)
        self.assertEqual(stats['range_service_call_count'], 2)
        range_svc = {row['city']: row['count'] for row in stats['range_service_city_stats']}
        self.assertEqual(range_svc.get('Mumbai'), 1)
        self.assertEqual(range_svc.get('Pune'), 1)
        # city_stats = unique new bookings only (not all jobs / service calls).
        self.assertEqual(stats['city_stats'], [{'city': 'Mumbai', 'count': 1}])
        self.assertEqual(stats['range_booking_city_stats'], stats['city_stats'])

    def test_multi_service_children_count_as_one_new_booking(self):
        """One package with 3 service rows must contribute Mumbai — 1, not 3."""
        parent = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants, Termite, Rodent',
            city='Mumbai',
            schedule_datetime=self.today,
            price='5000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            is_service_call=False,
        )
        for svc in ('Cockroach / Ants', 'Termite', 'Rodent'):
            JobCard.objects.create(
                client=self.client_record,
                parent_job=parent,
                source_service=svc,
                service_type=svc,
                city='Mumbai',
                schedule_datetime=self.today,
                price='0',
                reference='Other',
                status=JobCard.JobStatus.PENDING,
                booking_type=JobCard.BookingType.NEW_BOOKING,
                service_cycle=1,
                is_auto_generated=True,
                is_service_call=False,
            )
        # Follow-up service call must not inflate new-booking city count.
        JobCard.objects.create(
            client=self.client_record,
            parent_job=parent,
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

        stats = DashboardService.get_dashboard_statistics(
            from_date=timezone.now().date().isoformat(),
            to_date=timezone.now().date().isoformat(),
        )
        self.assertEqual(stats['range_booking_count'], 1)
        self.assertEqual(stats['city_stats'], [{'city': 'Mumbai', 'count': 1}])
        self.assertEqual(stats['range_booking_city_stats'], [{'city': 'Mumbai', 'count': 1}])
        self.assertEqual(stats['today_booking_count'], 1)
        self.assertGreaterEqual(stats['today_service_call_count'], 1)

    def test_city_stats_merge_case_variants_and_show_proper_names(self):
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            city='Mumbai',
            schedule_datetime=self.today,
            price='1000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            booking_type=JobCard.BookingType.NEW_BOOKING,
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            city='mumbai',
            schedule_datetime=self.today,
            price='1000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            booking_type=JobCard.BookingType.NEW_BOOKING,
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            city='Navi mumbai',
            schedule_datetime=self.today,
            price='1000',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            booking_type=JobCard.BookingType.NEW_BOOKING,
        )

        stats = DashboardService.get_dashboard_statistics()
        by_city = {row['city']: row['count'] for row in stats['today_city_stats']}
        self.assertEqual(by_city.get('Mumbai'), 2)
        self.assertEqual(by_city.get('Navi Mumbai'), 1)
        self.assertNotIn('mumbai', by_city)

    def test_today_complaint_calls_are_split_from_bookings(self):
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
        complaint = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            city='Mumbai',
            schedule_datetime=self.today,
            price='0',
            reference='Other',
            status=JobCard.JobStatus.ON_PROCESS,
            booking_type=JobCard.BookingType.COMPLAINT_CALL,
            booking_category=JobCard.BookingCategory.COMPLAINT_CALL,
            is_complaint_call=True,
            is_service_call=False,
        )

        stats = DashboardService.get_dashboard_statistics(
            from_date=timezone.now().date().isoformat(),
            to_date=timezone.now().date().isoformat(),
        )
        self.assertEqual(stats['today_booking_count'], 1)
        self.assertEqual(stats['today_service_call_count'], 0)
        self.assertEqual(stats['today_complaint_call_count'], 1)
        self.assertEqual(stats['total_complaint_calls'], 1)
        self.assertEqual(stats['total_job_cards'], 2)
        self.assertEqual(stats['today_city_stats'], [{'city': 'Mumbai', 'count': 1}])
        self.assertEqual(stats['today_complaint_city_stats'], [{'city': 'Mumbai', 'count': 1}])
        self.assertTrue(complaint.is_complaint_call)


    def test_today_bookings_exclude_day1_multi_service_children(self):
        """Dashboard bookings must match Job Cards list (hide day-1 clones)."""
        parent = JobCard.objects.create(
            client=self.client_record,
            service_type='Termite, Cockroach / Ants',
            city='Mumbai',
            schedule_datetime=self.today,
            price='4000',
            reference='Other',
            status=JobCard.JobStatus.ON_PROCESS,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            is_service_call=False,
        )
        JobCard.objects.create(
            client=self.client_record,
            parent_job=parent,
            service_type='Termite',
            source_service='Termite',
            city='Mumbai',
            schedule_datetime=self.today,
            price='2500',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            service_cycle=1,
            is_auto_generated=True,
            is_service_call=False,
        )
        JobCard.objects.create(
            client=self.client_record,
            parent_job=parent,
            service_type='Cockroach / Ants',
            source_service='Cockroach / Ants',
            city='Mumbai',
            schedule_datetime=self.today,
            price='1500',
            reference='Other',
            status=JobCard.JobStatus.PENDING,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            service_cycle=1,
            is_auto_generated=True,
            is_service_call=False,
        )

        stats = DashboardService.get_dashboard_statistics(
            from_date=timezone.now().date().isoformat(),
            to_date=timezone.now().date().isoformat(),
        )
        self.assertEqual(stats['today_booking_count'], 1)
        self.assertEqual(stats['today_city_stats'], [{'city': 'Mumbai', 'count': 1}])
        # Pending day-1 children must not inflate Today Focus pending.
        self.assertEqual(stats['status_stats']['pending'], 0)
        self.assertEqual(stats['status_stats']['on_process'], 1)


class RevenueSharingBreakdownTests(TestCase):
    """Day-wise / month-wise 40% tech / 60% company sharing on Dashboard."""

    def setUp(self):
        self.client_record = Client.objects.create(full_name='Share Client', mobile='9000000088')
        self.today = timezone.localdate()
        self.month_start = self.today.replace(day=1)
        self.today_dt = timezone.make_aware(datetime.combine(self.today, datetime.min.time()))
        earlier = self.month_start if self.today.day > 1 else self.today
        self.earlier_day = earlier
        self.earlier_dt = timezone.make_aware(datetime.combine(self.earlier_day, datetime.min.time()))

    def test_price_fallback_splits_40_60(self):
        from core.services import build_revenue_sharing_breakdown

        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='10000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=timezone.now(),
        )
        data = build_revenue_sharing_breakdown(from_date=self.today, to_date=self.today)
        self.assertEqual(data['technician_percent'], 40.0)
        self.assertEqual(data['company_percent'], 60.0)
        self.assertEqual(data['summary']['bookings'], 1)
        self.assertEqual(data['summary']['revenue'], 10000.0)
        self.assertEqual(data['summary']['technician_share'], 4000.0)
        self.assertEqual(data['summary']['company_share'], 6000.0)
        self.assertEqual(len(data['daily']), 1)
        self.assertEqual(data['daily'][0]['date'], self.today.isoformat())
        self.assertEqual(data['monthly'][0]['bookings'], 1)

    def test_uses_visit_revenue_snapshots_when_present(self):
        from decimal import Decimal

        from core.services import build_revenue_sharing_breakdown

        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='999',  # ignored when visit snapshot set
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=timezone.now(),
            visit_revenue_amount=Decimal('5000.00'),
            technician_pool_amount=Decimal('2000.00'),
            company_share_amount=Decimal('3000.00'),
        )
        data = build_revenue_sharing_breakdown(from_date=self.today, to_date=self.today)
        self.assertEqual(data['summary']['revenue'], 5000.0)
        self.assertEqual(data['summary']['technician_share'], 2000.0)
        self.assertEqual(data['summary']['company_share'], 3000.0)

    def test_excludes_complaints_and_salaried(self):
        from core.services import build_revenue_sharing_breakdown

        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='8000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=timezone.now(),
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='3000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.COMPLAINT_CALL,
            booking_category=JobCard.BookingCategory.COMPLAINT_CALL,
            is_complaint_call=True,
            completed_at=timezone.now(),
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='4000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            payment_model=JobCard.PaymentModel.SALARIED,
            completed_at=timezone.now(),
        )
        data = build_revenue_sharing_breakdown(from_date=self.today, to_date=self.today)
        self.assertEqual(data['summary']['bookings'], 1)
        self.assertEqual(data['summary']['revenue'], 8000.0)

    def test_excludes_service_calls_and_amc_followups(self):
        """The 40/60 pool is booking revenue only.

        A service call / AMC follow-up visit carries a visit amount, but that
        money was already counted on the booking it belongs to, so letting it
        into this report inflated Total Revenue and both shares.
        """
        from core.services import build_revenue_sharing_breakdown

        booking = JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='8000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=timezone.now(),
        )
        # Service call re-visit on the same booking.
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='1500',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            is_service_call=True,
            completed_at=timezone.now(),
        )
        # AMC follow-up visit.
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='2500',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
            booking_category=JobCard.BookingCategory.AMC_FOLLOWUP,
            is_followup_visit=True,
            completed_at=timezone.now(),
        )
        # Day-1 auto-generated child of a multi-service package.
        JobCard.objects.create(
            client=self.client_record,
            service_type='Termite',
            schedule_datetime=self.today_dt,
            price='3500',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            parent_job=booking,
            service_cycle=1,
            is_auto_generated=True,
            completed_at=timezone.now(),
        )

        data = build_revenue_sharing_breakdown(from_date=self.today, to_date=self.today)
        self.assertEqual(data['summary']['bookings'], 1)
        self.assertEqual(data['summary']['revenue'], 8000.0)
        self.assertEqual(data['summary']['technician_share'], 3200.0)
        self.assertEqual(data['summary']['company_share'], 4800.0)

    def test_sharing_revenue_matches_dashboard_revenue_kpi(self):
        """Both reports must agree; they now share one predicate."""
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='6000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=timezone.now(),
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='1200',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            is_service_call=True,
            completed_at=timezone.now(),
        )
        stats = DashboardService.get_dashboard_statistics(
            from_date=self.today.isoformat(),
            to_date=self.today.isoformat(),
        )
        self.assertEqual(stats['sharing_breakdown']['summary']['revenue'], 6000.0)

    def test_dashboard_single_day_filter_expands_sharing_to_month(self):
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.earlier_dt,
            price='5000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=timezone.now(),
        )
        JobCard.objects.create(
            client=self.client_record,
            service_type='Cockroach / Ants',
            schedule_datetime=self.today_dt,
            price='5000',
            reference='Other',
            status=JobCard.JobStatus.DONE,
            booking_type=JobCard.BookingType.NEW_BOOKING,
            completed_at=timezone.now(),
        )
        stats = DashboardService.get_dashboard_statistics(
            from_date=self.today.isoformat(),
            to_date=self.today.isoformat(),
        )
        sharing = stats['sharing_breakdown']
        self.assertEqual(sharing['from'], self.month_start.isoformat())
        self.assertEqual(sharing['to'], self.today.isoformat())
        self.assertEqual(sharing['summary']['bookings'], 2)
        self.assertEqual(sharing['summary']['revenue'], 10000.0)
        self.assertEqual(sharing['summary']['technician_share'], 4000.0)
        self.assertEqual(sharing['summary']['company_share'], 6000.0)
        self.assertGreaterEqual(len(sharing['daily']), 1)
        self.assertEqual(len(sharing['monthly']), 1)
