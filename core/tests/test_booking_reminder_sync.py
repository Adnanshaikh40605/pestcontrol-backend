"""
A reminder set on a booking must reach the CRM Reminders tab.

Before this, JobCard.reminder_* saved fine but the tab is backed by the
Reminder table, whose inquiry_type could only be an inquiry — so booking
follow-ups were effectively write-only.
"""
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.models import Client, JobCard, Reminder


def booking_reminders(jobcard=None, *, status=None):
    qs = Reminder.objects.filter(inquiry_type=Reminder.InquiryType.BOOKING)
    if jobcard is not None:
        qs = qs.filter(inquiry_id=jobcard.id)
    if status is not None:
        qs = qs.filter(status=status)
    return qs


class BookingReminderSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('desk', password='x')
        self.client_record = Client.objects.create(
            full_name='Asha Rao',
            mobile='9876543210',
            city='Mumbai',
            state='Maharashtra',
        )
        self.tomorrow = timezone.localdate() + timedelta(days=1)

    def make_booking(self, **overrides):
        fields = dict(
            client=self.client_record,
            client_address='12 Hill Road',
            service_type='Cockroach Standard',
            schedule_datetime=timezone.now() + timedelta(days=1),
            price=1500,
            city='Mumbai',
            state='Maharashtra',
            created_by=self.user,
        )
        fields.update(overrides)
        return JobCard.objects.create(**fields)

    def test_a_booking_without_a_reminder_creates_nothing(self):
        self.make_booking()
        self.assertEqual(booking_reminders().count(), 0)

    def test_setting_a_reminder_puts_it_on_the_reminders_tab(self):
        booking = self.make_booking(
            reminder_date=self.tomorrow,
            reminder_time=time(14, 30),
            reminder_note='Call about the kitchen',
        )

        reminder = booking_reminders(booking).get()
        self.assertEqual(reminder.reminder_date, self.tomorrow)
        self.assertEqual(reminder.reminder_time, time(14, 30))
        self.assertEqual(reminder.note, 'Call about the kitchen')
        self.assertEqual(reminder.status, Reminder.ReminderStatus.PENDING)

    def test_the_reminder_carries_the_customer_so_the_tab_can_show_it(self):
        booking = self.make_booking(reminder_date=self.tomorrow)

        reminder = booking_reminders(booking).get()
        self.assertEqual(reminder.customer_name, 'Asha Rao')
        self.assertEqual(reminder.mobile_number, '9876543210')
        self.assertEqual(reminder.created_by, self.user)

    def test_a_reminder_with_no_note_still_reads_sensibly(self):
        booking = self.make_booking(reminder_date=self.tomorrow, reminder_note='')
        self.assertEqual(booking_reminders(booking).get().note, 'Booking follow-up')

    def test_a_missing_client_mobile_does_not_block_the_mirror(self):
        self.client_record.mobile = ''
        self.client_record.save()
        booking = self.make_booking(reminder_date=self.tomorrow)

        # The reminder still has to appear; staff can look the number up.
        self.assertEqual(booking_reminders(booking).get().mobile_number, '')

    def test_editing_the_reminder_moves_it_instead_of_duplicating(self):
        booking = self.make_booking(
            reminder_date=self.tomorrow,
            reminder_time=time(9, 0),
            reminder_note='First plan',
        )
        later = self.tomorrow + timedelta(days=3)

        booking.reminder_date = later
        booking.reminder_time = time(16, 45)
        booking.reminder_note = 'Pushed back'
        booking.save()

        reminder = booking_reminders(booking).get()  # .get() proves there is only one
        self.assertEqual(reminder.reminder_date, later)
        self.assertEqual(reminder.reminder_time, time(16, 45))
        self.assertEqual(reminder.note, 'Pushed back')

    def test_clearing_the_reminder_takes_it_off_the_tab(self):
        booking = self.make_booking(reminder_date=self.tomorrow)
        self.assertEqual(booking_reminders(booking).count(), 1)

        booking.reminder_date = None
        booking.reminder_time = None
        booking.save()

        self.assertEqual(booking_reminders(booking).count(), 0)

    def test_marking_it_done_on_the_booking_keeps_it_as_history(self):
        booking = self.make_booking(reminder_date=self.tomorrow)

        booking.is_reminder_done = True
        booking.save()

        self.assertEqual(booking_reminders(booking, status=Reminder.ReminderStatus.PENDING).count(), 0)
        self.assertEqual(booking_reminders(booking, status=Reminder.ReminderStatus.COMPLETED).count(), 1)

    def test_reopening_a_reminder_makes_it_outstanding_again(self):
        booking = self.make_booking(reminder_date=self.tomorrow, is_reminder_done=True)
        self.assertEqual(booking_reminders(booking, status=Reminder.ReminderStatus.PENDING).count(), 0)

        booking.is_reminder_done = False
        booking.save()

        self.assertEqual(booking_reminders(booking, status=Reminder.ReminderStatus.PENDING).count(), 1)

    def test_deleting_the_booking_removes_its_reminder(self):
        booking = self.make_booking(reminder_date=self.tomorrow)
        self.assertEqual(booking_reminders().count(), 1)

        booking.delete()

        # inquiry_id is a plain integer, so nothing else would clean this up.
        self.assertEqual(booking_reminders().count(), 0)

    def test_an_unrelated_save_does_not_disturb_the_reminder(self):
        booking = self.make_booking(reminder_date=self.tomorrow)
        original = booking_reminders(booking).get()

        booking.status = 'Completed'
        booking.save(update_fields=['status'])

        self.assertEqual(booking_reminders(booking).get().id, original.id)

    def test_two_bookings_keep_separate_reminders(self):
        first = self.make_booking(reminder_date=self.tomorrow, reminder_note='One')
        second = self.make_booking(reminder_date=self.tomorrow, reminder_note='Two')

        self.assertEqual(booking_reminders(first).get().note, 'One')
        self.assertEqual(booking_reminders(second).get().note, 'Two')


class ReminderMobileNormalisationTests(TestCase):
    """
    Reminder.mobile_number is 10 chars. Client.mobile is too, so a country code
    cannot reach here through the database — but the mirror also runs during the
    backfill over historical rows, so it stays defensive.
    """

    def test_it_keeps_a_plain_ten_digit_number(self):
        from core.reminder_sync import _mobile_for_reminder

        self.assertEqual(_mobile_for_reminder('9876543210'), '9876543210')

    def test_it_strips_a_country_code_rather_than_overflowing(self):
        from core.reminder_sync import _mobile_for_reminder

        self.assertEqual(_mobile_for_reminder('+919876543210'), '9876543210')

    def test_it_strips_formatting(self):
        from core.reminder_sync import _mobile_for_reminder

        self.assertEqual(_mobile_for_reminder('98765 43210'), '9876543210')

    def test_it_tolerates_a_blank_or_missing_number(self):
        from core.reminder_sync import _mobile_for_reminder

        self.assertEqual(_mobile_for_reminder(''), '')
        self.assertEqual(_mobile_for_reminder(None), '')


class BookingReminderCompletionTests(TestCase):
    """Completing from the Reminders tab must write back to the booking."""

    def setUp(self):
        self.user = User.objects.create_user('desk2', password='x')
        self.client_record = Client.objects.create(
            full_name='Vikram Shah',
            mobile='9123456780',
            city='Mumbai',
            state='Maharashtra',
        )
        self.booking = JobCard.objects.create(
            client=self.client_record,
            client_address='4 Marine Drive',
            service_type='Cockroach Premium',
            schedule_datetime=timezone.now() + timedelta(days=1),
            price=2500,
            city='Mumbai',
            state='Maharashtra',
            created_by=self.user,
            reminder_date=timezone.localdate() + timedelta(days=1),
            reminder_time=time(11, 0),
        )

    def test_completing_the_reminder_marks_the_booking_done(self):
        from core.reminder_sync import mark_source_inquiry_reminder_done

        reminder = booking_reminders(self.booking).get()
        reminder.status = Reminder.ReminderStatus.COMPLETED
        reminder.save(update_fields=['status'])
        mark_source_inquiry_reminder_done(reminder)

        self.booking.refresh_from_db()
        self.assertTrue(self.booking.is_reminder_done)

    def test_completing_does_not_bounce_back_and_reopen_itself(self):
        from core.reminder_sync import mark_source_inquiry_reminder_done

        reminder = booking_reminders(self.booking).get()
        reminder.status = Reminder.ReminderStatus.COMPLETED
        reminder.save(update_fields=['status'])
        mark_source_inquiry_reminder_done(reminder)

        # The write-back uses .update(), which skips post_save, so no new
        # pending row should appear for this booking.
        self.assertEqual(booking_reminders(self.booking, status=Reminder.ReminderStatus.PENDING).count(), 0)
        self.assertEqual(booking_reminders(self.booking).count(), 1)


class BookingReminderApiTests(TestCase):
    """The tab reads /api/v1/reminders/, so booking rows must come back there."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin-rem', 'a@b.com', 'x')
        self.api = self.client
        self.api.force_login(self.user)
        self.client_record = Client.objects.create(
            full_name='Nita Kulkarni',
            mobile='9012345678',
            city='Mumbai',
            state='Maharashtra',
        )
        self.booking = JobCard.objects.create(
            client=self.client_record,
            client_address='9 Linking Road',
            service_type='Cockroach Standard',
            schedule_datetime=timezone.now() + timedelta(days=1),
            price=1800,
            city='Mumbai',
            state='Maharashtra',
            created_by=self.user,
            reminder_date=timezone.localdate(),
            reminder_time=time(10, 15),
            reminder_note='Confirm access',
        )

    def test_the_reminders_endpoint_returns_the_booking_reminder(self):
        res = self.api.get('/api/v1/reminders/')
        self.assertEqual(res.status_code, 200)

        rows = res.json().get('results', res.json())
        mine = [r for r in rows if r['inquiry_type'] == 'booking' and r['inquiry_id'] == self.booking.id]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]['customer_name'], 'Nita Kulkarni')
        self.assertEqual(mine[0]['note'], 'Confirm access')

    def test_the_endpoint_can_be_filtered_to_booking_reminders(self):
        res = self.api.get('/api/v1/reminders/?inquiry_type=booking')
        self.assertEqual(res.status_code, 200)

        rows = res.json().get('results', res.json())
        self.assertTrue(rows)
        self.assertTrue(all(r['inquiry_type'] == 'booking' for r in rows))

    def test_editing_on_the_tab_writes_back_to_the_booking(self):
        reminder = booking_reminders(self.booking).get()
        moved_to = str(timezone.localdate() + timedelta(days=5))

        res = self.api.patch(
            f'/api/v1/reminders/{reminder.id}/',
            data={'reminder_date': moved_to, 'note': 'Moved on the tab'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(str(self.booking.reminder_date), moved_to)
        self.assertEqual(self.booking.reminder_note, 'Moved on the tab')

    def test_an_edit_on_the_tab_survives_a_later_booking_save(self):
        reminder = booking_reminders(self.booking).get()
        moved_to = str(timezone.localdate() + timedelta(days=6))

        self.api.patch(
            f'/api/v1/reminders/{reminder.id}/',
            data={'reminder_date': moved_to},
            content_type='application/json',
        )

        # The booking is the source of truth, so saving it must not revert
        # the edit that was just made on the tab.
        self.booking.refresh_from_db()
        self.booking.save()

        self.assertEqual(str(booking_reminders(self.booking).get().reminder_date), moved_to)

    def test_mark_complete_from_the_tab_closes_the_booking_reminder(self):
        reminder = booking_reminders(self.booking).get()

        res = self.api.post(f'/api/v1/reminders/{reminder.id}/mark_complete/')
        self.assertEqual(res.status_code, 200)

        reminder.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(reminder.status, Reminder.ReminderStatus.COMPLETED)
        self.assertTrue(self.booking.is_reminder_done)


class BookingReminderBackfillTests(TestCase):
    """Bookings that predate the sync should be brought across."""

    def test_backfill_picks_up_an_unmirrored_booking(self):
        from core.reminder_sync import backfill_legacy_reminders

        user = User.objects.create_user('desk3', password='x')
        client_record = Client.objects.create(
            full_name='Old Booking',
            mobile='9000000001',
            city='Mumbai',
            state='Maharashtra',
        )
        booking = JobCard.objects.create(
            client=client_record,
            client_address='1 Old Street',
            service_type='Cockroach Standard',
            schedule_datetime=timezone.now() + timedelta(days=1),
            price=1000,
            city='Mumbai',
            state='Maharashtra',
            created_by=user,
            reminder_date=date(2026, 12, 1),
        )
        # Simulate the pre-change state, where no mirror row existed.
        booking_reminders(booking).delete()
        self.assertEqual(booking_reminders(booking).count(), 0)

        backfill_legacy_reminders()

        self.assertEqual(booking_reminders(booking).count(), 1)

    def test_backfill_does_not_double_up_on_an_already_mirrored_booking(self):
        from core.reminder_sync import backfill_legacy_reminders

        user = User.objects.create_user('desk4', password='x')
        client_record = Client.objects.create(
            full_name='Already Synced',
            mobile='9000000002',
            city='Mumbai',
            state='Maharashtra',
        )
        booking = JobCard.objects.create(
            client=client_record,
            client_address='2 New Street',
            service_type='Cockroach Standard',
            schedule_datetime=timezone.now() + timedelta(days=1),
            price=1000,
            city='Mumbai',
            state='Maharashtra',
            created_by=user,
            reminder_date=date(2026, 12, 2),
        )
        self.assertEqual(booking_reminders(booking).count(), 1)

        backfill_legacy_reminders()

        self.assertEqual(booking_reminders(booking).count(), 1)
