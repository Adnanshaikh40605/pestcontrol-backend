from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import CRMInquiry, Reminder
from core.reminder_sync import (
    backfill_legacy_reminders,
    mark_source_inquiry_reminder_done,
    sync_legacy_reminder_for_inquiry,
)


class ReminderSyncTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='9000000001', password='testpass')

    def test_backfill_creates_unified_reminder_from_crm_inquiry(self):
        inquiry = CRMInquiry.objects.create(
            name='Test Customer',
            mobile='9876543210',
            reminder_date=date(2026, 6, 15),
            reminder_time=time(10, 0),
            reminder_note='Call back about AMC',
            created_by=self.user,
        )

        created = backfill_legacy_reminders()

        self.assertEqual(created, 1)
        reminder = Reminder.objects.get()
        self.assertEqual(reminder.inquiry_type, Reminder.InquiryType.CRM)
        self.assertEqual(reminder.inquiry_id, inquiry.id)
        self.assertEqual(reminder.customer_name, 'Test Customer')
        self.assertEqual(reminder.status, Reminder.ReminderStatus.PENDING)

    def test_backfill_skips_duplicate_pending_reminder(self):
        inquiry = CRMInquiry.objects.create(
            name='Test Customer',
            mobile='9876543210',
            reminder_date=date(2026, 6, 15),
            reminder_note='Call back',
            created_by=self.user,
        )
        Reminder.objects.create(
            inquiry_type=Reminder.InquiryType.CRM,
            inquiry_id=inquiry.id,
            customer_name=inquiry.name,
            mobile_number=inquiry.mobile,
            reminder_date=inquiry.reminder_date,
            note='Existing reminder',
            status=Reminder.ReminderStatus.PENDING,
        )

        created = backfill_legacy_reminders()

        self.assertEqual(created, 0)
        self.assertEqual(Reminder.objects.count(), 1)

    def test_sync_legacy_reminder_for_inquiry_returns_none_when_done(self):
        inquiry = CRMInquiry.objects.create(
            name='Done Customer',
            mobile='9876543211',
            reminder_date=date(2026, 6, 10),
            is_reminder_done=True,
        )

        result = sync_legacy_reminder_for_inquiry(
            inquiry,
            Reminder.InquiryType.CRM,
        )

        self.assertIsNone(result)
        self.assertEqual(Reminder.objects.count(), 0)

    def test_mark_complete_syncs_legacy_inquiry_fields(self):
        inquiry = CRMInquiry.objects.create(
            name='Sync Customer',
            mobile='9876543212',
            reminder_date=date(2026, 6, 20),
            reminder_note='Follow up',
            created_by=self.user,
        )
        reminder = Reminder.objects.create(
            inquiry_type=Reminder.InquiryType.CRM,
            inquiry_id=inquiry.id,
            customer_name=inquiry.name,
            mobile_number=inquiry.mobile,
            reminder_date=inquiry.reminder_date,
            note='Follow up',
            status=Reminder.ReminderStatus.PENDING,
        )

        mark_source_inquiry_reminder_done(reminder)

        inquiry.refresh_from_db()
        self.assertTrue(inquiry.is_reminder_done)
