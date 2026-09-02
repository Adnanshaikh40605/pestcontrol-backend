from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    Client,
    Feedback,
    JobCard,
    JobCardTechnicianParticipation,
    SettlementLineItem,
    Technician,
    TechnicianSettlement,
)
from partner.models import Partner, PartnerEarning
from core.payment_utils import parse_jobcard_price


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianLedgerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ledger_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.tech = Technician.objects.create(
            name='Ledger Partner',
            mobile='9444000001',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Ledger Partner',
            mobile='9444000001',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
        )
        self.client_obj = Client.objects.create(
            full_name='Ledger Customer',
            mobile='9555000001',
        )

    def _job(
        self,
        *,
        status='Done',
        booking_type='New Booking',
        amount='1000',
        technician=None,
        partner=None,
        when=None,
        **overrides,
    ):
        now = when or timezone.now()
        technician = technician or self.tech
        partner = partner if partner is not None else self.partner
        fields = {
            'client': self.client_obj,
            'technician': technician,
            'partner': partner,
            'service_type': 'General Pest Control',
            'city': 'Pune',
            'job_type': JobCard.JobType.CUSTOMER,
            'booking_type': booking_type,
            'price': amount,
            'total_amount': Decimal(amount),
            'status': 'Pending',
            'schedule_datetime': now,
            'payment_model': JobCard.PaymentModel.REVENUE_SHARING,
            'payout_status': JobCard.PayoutStatus.PENDING,
            'created_by': self.user,
        }
        fields.update(overrides)
        job = JobCard.objects.create(**fields)
        if status == 'Done':
            JobCard.objects.filter(pk=job.pk).update(
                status=JobCard.JobStatus.DONE,
                completed_at=now,
                visit_revenue_amount=Decimal(amount),
                technician_pool_amount=Decimal(amount) * Decimal('0.40'),
                company_share_amount=Decimal(amount) * Decimal('0.60'),
                visit_payout_amount=Decimal(amount) * Decimal('0.40'),
            )
        elif status != 'Pending':
            JobCard.objects.filter(pk=job.pk).update(status=status)
        job.refresh_from_db()
        is_salaried = technician.technician_type == Technician.TechnicianType.SALARIED
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=technician,
            partner=partner,
            role=JobCardTechnicianParticipation.Role.LEAD,
            attendance_status=(
                JobCardTechnicianParticipation.AttendanceStatus.COMPLETED
                if status == 'Done'
                else JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED
            ),
            payout_amount_snapshot=(
                Decimal('0.00')
                if status != 'Done' or is_salaried
                else Decimal(amount) * Decimal('0.40')
            ),
        )
        return job

    def _ledger(self, params=None, technician=None):
        target = technician or self.tech
        return self.api.get(f'/api/v1/technicians/{target.id}/ledger/', params or {})

    def test_ledger_reports_booking_shares_and_paid_settlement(self):
        job = self._job(amount='1000')
        settlement = TechnicianSettlement.objects.create(
            technician=self.tech,
            partner=self.partner,
            period_start=timezone.localdate(),
            period_end=timezone.localdate(),
            status=TechnicianSettlement.Status.PAID,
            gross_amount=Decimal('400.00'),
            incentive_amount=Decimal('50.00'),
            deduction_amount=Decimal('20.00'),
            net_amount=Decimal('430.00'),
            paid_at=timezone.now(),
            paid_by=self.user,
        )
        participation = job.technician_participations.get(technician=self.tech)
        SettlementLineItem.objects.create(
            settlement=settlement,
            job=job,
            participation=participation,
            earning_type=SettlementLineItem.EarningType.REVENUE_SHARE,
            amount=Decimal('400.00'),
        )
        SettlementLineItem.objects.create(
            settlement=settlement,
            job=job,
            participation=participation,
            earning_type=SettlementLineItem.EarningType.INCENTIVE,
            amount=Decimal('50.00'),
        )
        SettlementLineItem.objects.create(
            settlement=settlement,
            job=job,
            participation=participation,
            earning_type=SettlementLineItem.EarningType.DEDUCTION,
            amount=Decimal('20.00'),
        )

        res = self.api.get(f'/api/v1/technicians/{self.tech.id}/ledger/')

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['count'], 1)
        row = res.data['results'][0]
        self.assertEqual(Decimal(row['technician_share']), Decimal('400.00'))
        self.assertEqual(Decimal(row['company_share']), Decimal('600.00'))
        self.assertEqual(Decimal(row['bonus']), Decimal('50.00'))
        self.assertEqual(Decimal(row['penalty']), Decimal('20.00'))
        self.assertEqual(Decimal(row['paid_amount']), Decimal('430.00'))
        self.assertEqual(Decimal(row['pending_amount']), Decimal('0.00'))
        self.assertEqual(Decimal(row['net_payable']), Decimal('430.00'))
        self.assertEqual(len(res.data['payment_history']), 1)

    def test_amc_pending_visit_has_no_share(self):
        job = self._job(
            status='Upcoming',
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
            amount='1000',
        )
        JobCard.objects.filter(pk=job.pk).update(
            service_category=JobCard.ServiceCategory.AMC,
            included_in_amc=True,
        )

        res = self.api.get(
            f'/api/v1/technicians/{self.tech.id}/ledger/',
            {'booking_type': 'amc'},
        )

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(Decimal(res.data['results'][0]['technician_share']), Decimal('0.00'))
        self.assertFalse(res.data['results'][0]['is_completed_visit'])

    def test_type_labels_one_time_amc_contract_amc(self):
        one = self._job(amount='1000')
        amc = self._job(
            amount='1000',
            booking_type=JobCard.BookingType.AMC_FOLLOWUP,
        )
        JobCard.objects.filter(pk=amc.pk).update(
            service_category=JobCard.ServiceCategory.AMC,
            included_in_amc=True,
            planned_visit_count=3,
        )
        contract_amc = self._job(
            amount='1000',
            booking_type=JobCard.BookingType.AMC_MAIN,
        )
        JobCard.objects.filter(pk=contract_amc.pk).update(
            service_category=JobCard.ServiceCategory.AMC,
            is_amc_main_booking=True,
            job_type=JobCard.JobType.SOCIETY,
            commercial_type=JobCard.CommercialType.SOCIETY,
            planned_visit_count=3,
        )
        res = self.api.get(f'/api/v1/technicians/{self.tech.id}/ledger/')
        self.assertEqual(res.status_code, 200, res.data)
        labels = {row['job_id']: row['booking_type_label'] for row in res.data['results']}
        self.assertEqual(labels[one.id], 'One Time')
        self.assertEqual(labels[amc.id], 'AMC')
        self.assertEqual(labels[contract_amc.id], 'Contract AMC')


    def test_bed_bugs_followup_booking_amount_is_half_package(self):
        root = self._job(
            amount='2500',
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '1 RK', 'amount': 2500},
            ],
            max_cycle=2,
            planned_visit_count=2,
            service_cycle=1,
            status='Done',
        )
        followup = self._job(
            amount='2500',
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '1 RK', 'amount': 2500},
            ],
            parent_job=root,
            max_cycle=2,
            planned_visit_count=2,
            service_cycle=2,
            is_followup_visit=True,
            is_service_call=True,
            status='Done',
        )
        res = self.api.get(f'/api/v1/technicians/{self.tech.id}/ledger/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['job_id'] == followup.id)
        self.assertEqual(row['booking_type_label'], '2-Service Package')
        self.assertEqual(row['service_number'], 'Service 2 of 2')
        # Bed Bugs follow-up should show per-visit value, not full package.
        self.assertEqual(Decimal(row['booking_amount']), Decimal('1250.00'))

    def test_bed_bugs_ledger_is_two_service_package_not_one_time(self):
        job = self._job(
            amount='1900',
            service_type='Bed Bugs',
            source_service='Bed Bugs',
            service_items=[
                {'service': 'Bed Bugs', 'plan': 'One Time Service', 'area': '1 RK', 'amount': 1900},
            ],
            max_cycle=1,
            planned_visit_count=1,
            service_cycle=1,
        )
        res = self.api.get(f'/api/v1/technicians/{self.tech.id}/ledger/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['job_id'] == job.id)
        self.assertEqual(row['booking_type_label'], '2-Service Package')
        self.assertEqual(row['service_number'], 'Service 1 of 2')
        self.assertEqual(row['planned_visits'], 2)

    def test_unsettled_bonus_is_in_pending_payable(self):
        job = self._job(amount='1000')
        PartnerEarning.objects.create(
            partner=self.partner,
            job=job,
            amount=Decimal('75.00'),
            earning_type=PartnerEarning.EarningType.INCENTIVE,
            is_approved=True,
        )
        res = self.api.get(f'/api/v1/technicians/{self.tech.id}/ledger/')
        row = res.data['results'][0]
        self.assertEqual(Decimal(row['bonus']), Decimal('75.00'))
        self.assertEqual(Decimal(row['net_payable']), Decimal('475.00'))
        self.assertEqual(Decimal(row['pending_amount']), Decimal('475.00'))

    def test_status_and_pagination_filters(self):
        self._job(status='Done', amount='1000')
        self._job(status='Upcoming', amount='2000')
        res = self.api.get(
            f'/api/v1/technicians/{self.tech.id}/ledger/',
            {'status': 'Done', 'page': 1, 'page_size': 1},
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['page_size'], 1)
        self.assertEqual(res.data['summary']['completed_jobs'], 1)

    def test_ledger_default_page_size(self):
        from core.technician_ledger import LEDGER_DEFAULT_PAGE_SIZE, LEDGER_MAX_PAGE_SIZE

        self.assertEqual(LEDGER_DEFAULT_PAGE_SIZE, 150)
        self.assertEqual(LEDGER_MAX_PAGE_SIZE, 150)
        # Cap is 150 — requesting more still returns at most max.
        for _ in range(5):
            self._job(status='Done', amount='1000')
        res = self._ledger({'page_size': 999})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['page_size'], LEDGER_MAX_PAGE_SIZE)
        self.assertEqual(len(res.data['results']), 5)
        self.assertEqual(res.data['count'], 5)

    def test_date_range_filter_excludes_outside_window(self):
        """Scenario: from/to window keeps only bookings inside the range."""
        inside = self._job(amount='1000', when=timezone.now() - timezone.timedelta(days=2))
        self._job(amount='4000', when=timezone.now() - timezone.timedelta(days=60))

        today = timezone.localdate()
        res = self._ledger({
            'from': (today - timezone.timedelta(days=7)).isoformat(),
            'to': today.isoformat(),
        })

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['job_id'], inside.id)
        self.assertEqual(Decimal(res.data['summary']['technician_share']), Decimal('400.00'))

    def test_city_and_service_type_filters_and_options(self):
        """Scenario: city/service filters narrow rows and options list real values."""
        self._job(amount='1000', city='Pune', service_type='General Pest Control')
        self._job(amount='2000', city='Lonavala', service_type='Termite Control')

        options = self._ledger().data['options']
        self.assertEqual(sorted(options['cities']), ['Lonavala', 'Pune'])
        self.assertEqual(
            sorted(options['service_types']),
            ['General Pest Control', 'Termite Control'],
        )

        res = self._ledger({'city': 'lonavala', 'service_type': 'termite'})
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['city'], 'Lonavala')
        self.assertEqual(Decimal(res.data['summary']['technician_share']), Decimal('800.00'))

    def test_salaried_technician_has_no_revenue_share(self):
        """Scenario: salaried staff show bookings but never earn a partner share."""
        salaried = Technician.objects.create(
            name='Salaried Staff',
            mobile='9444000009',
            technician_type=Technician.TechnicianType.SALARIED,
            is_active=True,
        )
        self._job(amount='1000', technician=salaried, partner=None)

        res = self._ledger(technician=salaried)

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['count'], 1)
        row = res.data['results'][0]
        self.assertEqual(Decimal(row['technician_share']), Decimal('0.00'))
        self.assertEqual(Decimal(row['net_payable']), Decimal('0.00'))
        self.assertEqual(Decimal(row['company_share']), Decimal('600.00'))
        self.assertEqual(Decimal(res.data['earnings']['lifetime']), Decimal('0.00'))

    def test_crew_member_sees_only_own_snapshot(self):
        """Scenario: crew member on a shared job sees their snapshot, not the lead's."""
        helper_tech = Technician.objects.create(
            name='Crew Partner',
            mobile='9444000002',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        helper_partner = Partner.objects.create(
            full_name='Helper Partner',
            mobile='9444000002',
            password='x',
            core_technician=helper_tech,
            is_app_approved=True,
        )
        job = self._job(amount='1000')
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=helper_tech,
            partner=helper_partner,
            role=JobCardTechnicianParticipation.Role.CREW,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
            payout_amount_snapshot=Decimal('150.00'),
        )

        helper_res = self._ledger(technician=helper_tech)
        lead_res = self._ledger()

        self.assertEqual(helper_res.data['count'], 1)
        self.assertEqual(
            Decimal(helper_res.data['results'][0]['technician_share']),
            Decimal('150.00'),
        )
        self.assertEqual(
            Decimal(lead_res.data['results'][0]['technician_share']),
            Decimal('400.00'),
        )

    def test_pagination_second_page_and_invalid_params(self):
        """Scenario: paging math is stable and bad page values fail loudly."""
        for index in range(5):
            self._job(amount='1000', when=timezone.now() - timezone.timedelta(days=index))

        page_two = self._ledger({'page': 2, 'page_size': 2})
        self.assertEqual(page_two.status_code, 200, page_two.data)
        self.assertEqual(page_two.data['count'], 5)
        self.assertEqual(page_two.data['total_pages'], 3)
        self.assertEqual(len(page_two.data['results']), 2)
        self.assertTrue(page_two.data['next'])
        self.assertTrue(page_two.data['previous'])

        beyond = self._ledger({'page': 9, 'page_size': 2})
        self.assertEqual(beyond.status_code, 200, beyond.data)
        self.assertEqual(beyond.data['results'], [])
        self.assertFalse(beyond.data['next'])

        invalid = self._ledger({'page': 'abc'})
        self.assertEqual(invalid.status_code, 400)

        # Summary always reflects every filtered row, not just the current page.
        self.assertEqual(
            Decimal(page_two.data['summary']['technician_share']),
            Decimal('2000.00'),
        )

    def test_cancelled_job_and_pending_settlement_stay_unpaid(self):
        """Scenario: cancelled visits earn nothing and draft settlements are not paid."""
        cancelled = self._job(status=JobCard.JobStatus.CANCELLED, amount='1000')
        done = self._job(amount='1000')
        settlement = TechnicianSettlement.objects.create(
            technician=self.tech,
            partner=self.partner,
            period_start=timezone.localdate(),
            period_end=timezone.localdate(),
            status=TechnicianSettlement.Status.DRAFT,
            gross_amount=Decimal('400.00'),
            net_amount=Decimal('400.00'),
        )
        SettlementLineItem.objects.create(
            settlement=settlement,
            job=done,
            participation=done.technician_participations.get(technician=self.tech),
            earning_type=SettlementLineItem.EarningType.REVENUE_SHARE,
            amount=Decimal('400.00'),
        )

        res = self._ledger()
        rows = {row['job_id']: row for row in res.data['results']}

        self.assertEqual(res.data['count'], 2)
        self.assertEqual(Decimal(rows[cancelled.id]['technician_share']), Decimal('0.00'))
        self.assertEqual(Decimal(rows[cancelled.id]['visit_revenue']), Decimal('0.00'))
        self.assertFalse(rows[cancelled.id]['is_completed_visit'])
        self.assertEqual(Decimal(rows[done.id]['paid_amount']), Decimal('0.00'))
        self.assertEqual(Decimal(rows[done.id]['pending_amount']), Decimal('400.00'))
        self.assertEqual(Decimal(res.data['summary']['pending_amount']), Decimal('400.00'))

    def test_contract_filter_and_average_rating(self):
        """Scenario: society work is contract economics and ratings average correctly."""
        society = self._job(
            amount='5000',
            job_type=JobCard.JobType.SOCIETY,
            property_type=JobCard.PropertyType.SOCIETY,
        )
        one_time = self._job(amount='1000')
        Feedback.objects.create(
            booking=society,
            rating=5,
            technician_behavior='excellent',
            feedback_type='Manual',
        )
        Feedback.objects.create(
            booking=one_time,
            rating=4,
            technician_behavior='good',
            feedback_type='Manual',
        )

        contract = self._ledger({'booking_type': 'contract'})
        self.assertEqual(contract.data['count'], 1)
        self.assertEqual(contract.data['results'][0]['booking_type'], 'contract')
        self.assertEqual(contract.data['summary']['contract_jobs'], 1)

        one_time_res = self._ledger({'booking_type': 'one_time'})
        self.assertEqual(one_time_res.data['count'], 1)
        self.assertEqual(one_time_res.data['results'][0]['job_id'], one_time.id)

        overall = self._ledger()
        self.assertEqual(Decimal(overall.data['summary']['average_rating']), Decimal('4.50'))

    def test_ledger_requires_authentication(self):
        """Scenario: the ledger is CRM-only and rejects anonymous callers."""
        self._job(amount='1000')
        anon = APIClient()

        res = anon.get(f'/api/v1/technicians/{self.tech.id}/ledger/')

        self.assertIn(res.status_code, (401, 403))

    def test_early_morning_visit_is_reported_on_local_day(self):
        """
        Scenario: IST runs ahead of UTC, so an early-morning visit must not slip
        back to the previous calendar day in the report.
        """
        local_today = timezone.localdate()
        early_morning = timezone.make_aware(
            timezone.datetime.combine(local_today, timezone.datetime.min.time())
            + timezone.timedelta(minutes=30)
        )
        self._job(amount='1000', when=early_morning)

        res = self._ledger({'from': local_today.isoformat(), 'to': local_today.isoformat()})

        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['booking_date'], local_today.isoformat())
        self.assertEqual(Decimal(res.data['earnings']['daily']), Decimal('400.00'))

    def test_ledger_uses_booking_schedule_date_not_completion_date(self):
        """Scenario: closed next day still shows under the booked schedule date."""
        booked_day = timezone.localdate() - timezone.timedelta(days=1)
        schedule = timezone.make_aware(
            timezone.datetime.combine(booked_day, timezone.datetime.strptime('09:30', '%H:%M').time())
        )
        completed = timezone.make_aware(
            timezone.datetime.combine(timezone.localdate(), timezone.datetime.strptime('11:00', '%H:%M').time())
        )
        job = self._job(amount='1000', when=schedule)
        JobCard.objects.filter(pk=job.pk).update(completed_at=completed)

        res = self._ledger({
            'from': booked_day.isoformat(),
            'to': booked_day.isoformat(),
        })

        self.assertEqual(res.data['count'], 1)
        self.assertEqual(int(res.data['results'][0]['booking_id']), job.id)
        self.assertEqual(res.data['results'][0]['booking_date'], booked_day.isoformat())

        # Must not appear under the completion day filter.
        next_day = self._ledger({
            'from': timezone.localdate().isoformat(),
            'to': timezone.localdate().isoformat(),
        })
        self.assertEqual(next_day.data['count'], 0)

    def test_booking_without_schedule_still_matches_date_range(self):
        """Scenario: a booking with no schedule falls back to its created date."""
        job = self._job(status='Pending', amount='1000')
        JobCard.objects.filter(pk=job.pk).update(schedule_datetime=None)
        today = timezone.localdate()

        res = self._ledger({'from': today.isoformat(), 'to': today.isoformat()})

        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['booking_date'], today.isoformat())

    def test_earnings_periods_track_today_month_and_lifetime(self):
        """Scenario: daily/monthly/lifetime earnings roll up completed visits only."""
        self._job(amount='1000')  # completed today
        self._job(status='Upcoming', amount='9000')  # never counted
        self._job(amount='2000', when=timezone.now() - timezone.timedelta(days=200))

        earnings = self._ledger().data['earnings']

        self.assertEqual(Decimal(earnings['daily']), Decimal('400.00'))
        self.assertEqual(Decimal(earnings['lifetime']), Decimal('1200.00'))
        self.assertGreaterEqual(Decimal(earnings['monthly']), Decimal('400.00'))

    def test_settle_selected_jobs_marks_settled_keeps_row(self):
        """Scenario: multi-select settle → Unsettled becomes Settled; row stays."""
        job_a = self._job(amount='1000')
        job_b = self._job(amount='2000')

        unsettled = self._ledger({'settlement_status': 'unsettled'})
        self.assertEqual(unsettled.status_code, 200, unsettled.data)
        self.assertEqual(unsettled.data['count'], 2)
        self.assertEqual(
            {row['settlement_status'] for row in unsettled.data['results']},
            {'unsettled'},
        )

        settle = self.api.post(
            f'/api/v1/technicians/{self.tech.id}/ledger/',
            {'job_ids': [job_a.id, job_b.id]},
            format='json',
        )
        self.assertEqual(settle.status_code, 200, settle.data)
        self.assertEqual(settle.data['job_count'], 2)
        self.assertEqual(Decimal(settle.data['net_amount']), Decimal('1200.00'))

        after = self._ledger({'settlement_status': 'settled'})
        self.assertEqual(after.data['count'], 2)
        for row in after.data['results']:
            self.assertEqual(row['settlement_status'], 'settled')
            self.assertEqual(row['settlement_status_label'], 'Settled')
            self.assertTrue(row['settlement_date'])
            self.assertEqual(Decimal(row['pending_amount']), Decimal('0.00'))

        # Still visible when filter is cleared
        all_rows = self._ledger({'settlement_status': ''})
        self.assertEqual(all_rows.data['count'], 2)

    def test_complaints_tab_isolated_and_client_number_exposed(self):
        """Complaints only on Complaints tab; main tabs exclude them; client mobile present."""
        normal = self._job(amount='1000')
        complaint = self._job(
            amount='0',
            is_complaint_call=True,
            booking_type=JobCard.BookingType.COMPLAINT_CALL,
            booking_category=JobCard.BookingCategory.COMPLAINT_CALL,
        )

        unsettled = self._ledger({'settlement_status': 'unsettled'})
        self.assertEqual(unsettled.status_code, 200, unsettled.data)
        unsettled_ids = {row['job_id'] for row in unsettled.data['results']}
        self.assertIn(normal.id, unsettled_ids)
        self.assertNotIn(complaint.id, unsettled_ids)

        all_rows = self._ledger({'settlement_status': ''})
        all_ids = {row['job_id'] for row in all_rows.data['results']}
        self.assertIn(normal.id, all_ids)
        self.assertNotIn(complaint.id, all_ids)

        complaints = self._ledger({'settlement_status': 'complaints'})
        self.assertEqual(complaints.status_code, 200, complaints.data)
        self.assertEqual(complaints.data['count'], 1)
        row = complaints.data['results'][0]
        self.assertEqual(row['job_id'], complaint.id)
        self.assertTrue(row['is_complaint_call'])
        self.assertEqual(row['client_mobile'], '9555000001')
        self.assertEqual(row['client_number'], '9555000001')

        normal_row = next(r for r in unsettled.data['results'] if r['job_id'] == normal.id)
        self.assertEqual(normal_row['client_mobile'], '9555000001')
        self.assertFalse(normal_row['is_complaint_call'])

    def test_move_to_old_service_and_remove_from_ledger(self):
        job = self._job(amount='1000')
        PartnerEarning.objects.create(
            partner=self.partner,
            job=job,
            amount=Decimal('400.00'),
            earning_type=PartnerEarning.EarningType.REVENUE_SHARE,
            is_approved=True,
        )

        move = self.api.post(
            f'/api/v1/technicians/{self.tech.id}/ledger/move-to-old-service/',
            {'job_id': job.id},
            format='json',
        )
        self.assertEqual(move.status_code, 200, move.data)
        job.refresh_from_db()
        self.assertEqual(job.payout_status, JobCard.PayoutStatus.LEGACY_EXEMPT)
        self.assertEqual(job.visit_payout_amount, Decimal('0.00'))
        self.assertFalse(PartnerEarning.objects.filter(job=job).exists())

        unsettled = self._ledger({'settlement_status': 'unsettled'})
        self.assertNotIn(job.id, {r['job_id'] for r in unsettled.data['results']})

        legacy = self._ledger({'settlement_status': 'legacy'})
        self.assertIn(job.id, {r['job_id'] for r in legacy.data['results']})
        legacy_row = next(r for r in legacy.data['results'] if r['job_id'] == job.id)
        self.assertEqual(legacy_row['settlement_status'], 'legacy')

        remove = self.api.post(
            f'/api/v1/technicians/{self.tech.id}/ledger/remove-booking/',
            {'job_id': job.id},
            format='json',
        )
        self.assertEqual(remove.status_code, 200, remove.data)
        job.refresh_from_db()
        self.assertTrue(job.hidden_from_technician_ledger)

        after_remove = self._ledger({'settlement_status': ''})
        self.assertNotIn(job.id, {r['job_id'] for r in after_remove.data['results']})
        legacy_after = self._ledger({'settlement_status': 'legacy'})
        self.assertNotIn(job.id, {r['job_id'] for r in legacy_after.data['results']})

    def test_ledger_heals_stale_amc_split_after_one_time_price_edit(self):
        """
        Regression #1930: AMC ₹2500 / 3 visits converted to One-Time ₹1000.
        History shows price 1000; ledger must not keep Booking 2500 / Service 833.33.
        """
        from core.payment_utils import effective_service_total

        job = self._job(
            amount='1000',
            service_type='Cockroach / Ants',
            service_items=[{
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'amount': 2500,
            }],
            total_amount=Decimal('2500.00'),
            planned_visit_count=3,
            max_cycle=3,
            service_category=JobCard.ServiceCategory.ONE_TIME,
            visit_revenue_amount=Decimal('833.33'),
            technician_pool_amount=Decimal('333.33'),
            company_share_amount=Decimal('500.00'),
            visit_payout_amount=Decimal('333.33'),
            payout_status=JobCard.PayoutStatus.PENDING,
        )
        # Simulate leftover AMC snapshot after staff edited price to 1000
        # (including paid amount still at the old package total).
        JobCard.objects.filter(pk=job.pk).update(
            price='1000',
            total_amount=Decimal('2500.00'),
            paid_amount=Decimal('2500.00'),
            pending_amount=Decimal('0.00'),
            visit_revenue_amount=Decimal('1000.00'),
            visit_payout_amount=Decimal('400.00'),
            technician_pool_amount=Decimal('400.00'),
            planned_visit_count=3,
            max_cycle=3,
            service_items=[{
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'amount': 2500,
            }],
        )
        job.refresh_from_db()
        part = job.technician_participations.get(technician=self.tech)
        part.payout_amount_snapshot = Decimal('400.00')
        part.save(update_fields=['payout_amount_snapshot', 'updated_at'])

        self.assertEqual(effective_service_total(job), Decimal('1000.00'))

        res = self._ledger({'settlement_status': 'unsettled'})
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['job_id'] == job.id)
        self.assertEqual(Decimal(row['booking_amount']), Decimal('1000.00'))
        self.assertEqual(Decimal(row['visit_revenue']), Decimal('1000.00'))
        self.assertEqual(Decimal(row['technician_share']), Decimal('400.00'))

        job.refresh_from_db()
        self.assertEqual(parse_jobcard_price(job.service_items[0]['amount']), Decimal('1000.00'))
        self.assertEqual(job.total_amount, Decimal('1000.00'))


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianLedgerLeadParticipationTests(TestCase):
    """Prevent duplicate LEAD rows from showing jobs on multiple ledgers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='lead_ledger_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_obj = Client.objects.create(
            full_name='Duplicate Lead Customer',
            mobile='9555000099',
        )
        self.kuldip = Technician.objects.create(
            name='Kuldip',
            mobile='9444000020',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        self.akshay = Technician.objects.create(
            name='Akshay Kumar',
            mobile='9444000005',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        Partner.objects.create(
            full_name='Kuldip',
            mobile='9444000020',
            password='x',
            core_technician=self.kuldip,
            is_app_approved=True,
        )
        Partner.objects.create(
            full_name='Akshay Kumar',
            mobile='9444000005',
            password='x',
            core_technician=self.akshay,
            is_app_approved=True,
        )

    def _job(self, technician):
        job = JobCard.objects.create(
            client=self.client_obj,
            technician=technician,
            assigned_to=technician.name,
            service_type='General Pest Control',
            city='Pune',
            price='1000',
            total_amount=Decimal('1000.00'),
            status=JobCard.JobStatus.DONE,
            schedule_datetime=timezone.now(),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            created_by=self.user,
        )
        from core.payout_engine import ensure_lead_participation

        ensure_lead_participation(job)
        return job

    def test_stale_lead_does_not_appear_on_wrong_ledger(self):
        job = self._job(self.kuldip)
        JobCardTechnicianParticipation.objects.create(
            jobcard=job,
            technician=self.akshay,
            role=JobCardTechnicianParticipation.Role.LEAD,
        )
        from core.payout_engine import enforce_single_lead_participation

        enforce_single_lead_participation(job)

        kuldip_ids = {
            r['job_id']
            for r in self.api.get(
                f'/api/v1/technicians/{self.kuldip.id}/ledger/',
            ).data['results']
        }
        akshay_ids = {
            r['job_id']
            for r in self.api.get(
                f'/api/v1/technicians/{self.akshay.id}/ledger/',
            ).data['results']
        }
        self.assertIn(job.id, kuldip_ids)
        self.assertNotIn(job.id, akshay_ids)

    def test_participants_api_rejects_second_lead(self):
        job = self._job(self.kuldip)
        res = self.api.post(
            f'/api/v1/jobcards/{job.id}/participants/',
            {'technician_id': self.akshay.id, 'role': 'lead'},
            format='json',
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(res.data.get('code'), 'lead_already_assigned')

    def test_reassign_clears_stale_lead(self):
        job = self._job(self.akshay)
        from core.payout_engine import reassign_job_technician

        reassign_job_technician(job, self.kuldip)
        leads = job.technician_participations.filter(
            role=JobCardTechnicianParticipation.Role.LEAD,
        )
        self.assertEqual(leads.count(), 1)
        self.assertEqual(leads.get().technician_id, self.kuldip.id)

