"""Remark-Based Call Activities — CRM + Website remarks count per staff."""
from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from core.models import CRMInquiry, Inquiry, InquiryRemark, WebsiteLeadRemark
from core.staff_remark_calls import get_remark_call_activity_report


class StaffRemarkCallActivityTests(APITestCase):
    def setUp(self):
        self.staff_a = User.objects.create_user(
            username='staff_a', password='pass1234', is_staff=True, first_name='Staff', last_name='A'
        )
        self.staff_b = User.objects.create_user(
            username='staff_b', password='pass1234', is_staff=True, first_name='Staff', last_name='B'
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.staff_a)

        self.crm = CRMInquiry.objects.create(
            name='CRM Lead',
            mobile='9000000001',
            pest_type='Cockroach',
            inquiry_date=timezone.localdate(),
            inquiry_time=timezone.localtime().time().replace(microsecond=0),
            status=CRMInquiry.InquiryStatus.NEW,
            created_by=self.staff_a,
        )
        self.web = Inquiry.objects.create(
            name='Web Lead',
            mobile='9000000002',
            message='Need service',
            service_interest='Cockroach',
            status=Inquiry.InquiryStatus.NEW,
        )

    def test_each_new_remark_counts_once_across_crm_and_website(self):
        InquiryRemark.objects.create(
            inquiry=self.crm, remark='Called customer', created_by=self.staff_a
        )
        WebsiteLeadRemark.objects.create(
            lead=self.web, remark='Followed up', created_by=self.staff_a
        )
        InquiryRemark.objects.create(
            inquiry=self.crm, remark='Other staff call', created_by=self.staff_b
        )

        report = get_remark_call_activity_report()
        by_id = {row['staff_id']: row for row in report['staff']}
        self.assertEqual(by_id[self.staff_a.id]['today'], 2)
        self.assertEqual(by_id[self.staff_a.id]['today_crm'], 1)
        self.assertEqual(by_id[self.staff_a.id]['today_website'], 1)
        self.assertEqual(by_id[self.staff_b.id]['today'], 1)

        today_board = {row['staff_id']: row['count'] for row in report['today']}
        self.assertEqual(today_board[self.staff_a.id], 2)
        self.assertEqual(today_board[self.staff_b.id], 1)

    def test_editing_remark_does_not_increase_count(self):
        entry = InquiryRemark.objects.create(
            inquiry=self.crm, remark='First note', created_by=self.staff_a
        )
        before = get_remark_call_activity_report()
        a_before = next(r for r in before['staff'] if r['staff_id'] == self.staff_a.id)['today']

        entry.remark = 'Edited note'
        entry.save(update_fields=['remark', 'updated_at'])

        after = get_remark_call_activity_report()
        a_after = next(r for r in after['staff'] if r['staff_id'] == self.staff_a.id)['today']
        self.assertEqual(a_before, 1)
        self.assertEqual(a_after, 1)

    def test_historical_remark_not_in_today(self):
        old = InquiryRemark.objects.create(
            inquiry=self.crm, remark='Old call', created_by=self.staff_a
        )
        # Force created_at to yesterday (preserve DB value after save)
        yesterday = timezone.localtime() - timedelta(days=1)
        InquiryRemark.objects.filter(pk=old.pk).update(created_at=yesterday)

        report = get_remark_call_activity_report()
        a = next(r for r in report['staff'] if r['staff_id'] == self.staff_a.id)
        self.assertEqual(a['today'], 0)
        self.assertEqual(a['yesterday'], 1)
        self.assertGreaterEqual(a['total'], 1)

    def test_api_endpoint_returns_combined_counts(self):
        InquiryRemark.objects.create(
            inquiry=self.crm, remark='CRM call', created_by=self.staff_a
        )
        WebsiteLeadRemark.objects.create(
            lead=self.web, remark='Web call', created_by=self.staff_a
        )
        res = self.api.get('/api/v1/dashboard/remark-call-activities/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['label'], 'Remark-Based Call Activities')
        a = next(r for r in res.data['staff'] if r['staff_id'] == self.staff_a.id)
        self.assertEqual(a['today'], 2)

    def test_api_staff_and_date_filters(self):
        InquiryRemark.objects.create(
            inquiry=self.crm, remark='A only', created_by=self.staff_a
        )
        InquiryRemark.objects.create(
            inquiry=self.crm, remark='B only', created_by=self.staff_b
        )
        today = timezone.localdate().isoformat()
        res = self.api.get(
            '/api/v1/dashboard/remark-call-activities/',
            {'staff_id': self.staff_a.id, 'from': today, 'to': today},
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(len(res.data['staff']), 1)
        self.assertEqual(res.data['staff'][0]['staff_id'], self.staff_a.id)
        self.assertEqual(res.data['staff'][0]['custom'], 1)
        self.assertEqual(res.data['selected_label'], today)
        selected = next(r for r in res.data['selected'] if r['staff_id'] == self.staff_a.id)
        self.assertEqual(selected['count'], 1)

    def test_selected_board_uses_custom_range_not_today(self):
        """From/to must drive selected board even when that day is not today."""
        old = InquiryRemark.objects.create(
            inquiry=self.crm, remark='Yesterday call', created_by=self.staff_a
        )
        yesterday = timezone.localdate() - timedelta(days=1)
        InquiryRemark.objects.filter(pk=old.pk).update(
            created_at=timezone.make_aware(datetime.combine(yesterday, time(12, 0)))
        )
        ymd = yesterday.isoformat()
        res = self.api.get(
            '/api/v1/dashboard/remark-call-activities/',
            {'from': ymd, 'to': ymd},
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['selected_label'], ymd)
        selected = next(r for r in res.data['selected'] if r['staff_id'] == self.staff_a.id)
        today_row = next(r for r in res.data['today'] if r['staff_id'] == self.staff_a.id)
        self.assertEqual(selected['count'], 1)
        self.assertEqual(today_row['count'], 0)

    def test_performance_endpoint_includes_remark_call_activities(self):
        InquiryRemark.objects.create(
            inquiry=self.crm, remark='Counted', created_by=self.staff_a
        )
        WebsiteLeadRemark.objects.create(
            lead=self.web, remark='Also counted', created_by=self.staff_a
        )
        res = self.api.get('/api/v1/dashboard/performance/', {'period': 'today'})
        self.assertEqual(res.status_code, 200, res.data)
        a = next(r for r in res.data if r['staff_id'] == self.staff_a.id)
        self.assertEqual(a['remark_call_activities'], 2)
        self.assertEqual(a['remark_call_activities_crm'], 1)
        self.assertEqual(a['remark_call_activities_website'], 1)

    def test_live_remark_create_apis_update_dashboard_counts(self):
        """POST CRM + Website remarks → Staff Performance counts update immediately."""
        before = self.api.get('/api/v1/dashboard/remark-call-activities/')
        self.assertEqual(before.status_code, 200, before.data)
        a_before = next(r for r in before.data['staff'] if r['staff_id'] == self.staff_a.id)['today']

        crm_res = self.api.post(
            f'/api/v1/crm-inquiries/{self.crm.id}/remarks/',
            {'remark': 'Live CRM follow-up call'},
            format='json',
        )
        self.assertEqual(crm_res.status_code, 201, crm_res.data)
        self.assertEqual(crm_res.data.get('created_by'), self.staff_a.id)

        web_res = self.api.post(
            f'/api/v1/website-leads/{self.web.id}/remarks/',
            {'remark': 'Live Website follow-up call'},
            format='json',
        )
        self.assertEqual(web_res.status_code, 201, web_res.data)
        self.assertEqual(web_res.data.get('created_by'), self.staff_a.id)

        # Second CRM remark by same staff must add +1 more (not replace).
        crm_res2 = self.api.post(
            f'/api/v1/crm-inquiries/{self.crm.id}/remarks/',
            {'remark': 'Second CRM call same day'},
            format='json',
        )
        self.assertEqual(crm_res2.status_code, 201, crm_res2.data)

        after = self.api.get('/api/v1/dashboard/remark-call-activities/')
        self.assertEqual(after.status_code, 200, after.data)
        a_after = next(r for r in after.data['staff'] if r['staff_id'] == self.staff_a.id)
        self.assertEqual(a_after['today'], a_before + 3)
        self.assertEqual(a_after['today_crm'], 2)
        self.assertEqual(a_after['today_website'], 1)

        board = next(r for r in after.data['today'] if r['staff_id'] == self.staff_a.id)
        self.assertEqual(board['count'], a_before + 3)

        # Editing existing remark text (same row / created_at) must not inflate count.
        remark_id = crm_res.data['id']
        InquiryRemark.objects.filter(pk=remark_id).update(remark='Edited live CRM follow-up')
        after_edit = self.api.get('/api/v1/dashboard/remark-call-activities/')
        a_edit = next(r for r in after_edit.data['staff'] if r['staff_id'] == self.staff_a.id)
        self.assertEqual(a_edit['today'], a_before + 3)
