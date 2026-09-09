"""
Sync legacy inquiry/booking reminder fields into the unified Reminder table.
"""
from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import User

from .models import CRMInquiry, Inquiry, JobCard, Reminder

#: Booking fields that feed the mirrored Reminder row.
BOOKING_REMINDER_FIELDS = frozenset(
    {'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done'}
)


def _mobile_for_reminder(value: Optional[str]) -> str:
    """
    Reminder.mobile_number is 10 chars, but a booking's mobile may carry a
    country code or formatting. Keep the last 10 digits so a stored booking can
    never fail to mirror on a field width.
    """
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    return digits[-10:]


def _pending_reminder_exists(
    inquiry_type: str,
    inquiry_id: int,
    reminder_date,
) -> bool:
    return Reminder.objects.filter(
        inquiry_type=inquiry_type,
        inquiry_id=inquiry_id,
        reminder_date=reminder_date,
        status=Reminder.ReminderStatus.PENDING,
    ).exists()


def sync_legacy_reminder_for_inquiry(
    inquiry,
    inquiry_type: str,
    *,
    created_by: Optional[User] = None,
) -> Optional[Reminder]:
    """Create a unified Reminder from legacy fields on an inquiry record."""
    if not inquiry.reminder_date or inquiry.is_reminder_done:
        return None

    if _pending_reminder_exists(inquiry_type, inquiry.id, inquiry.reminder_date):
        return None

    note = (inquiry.reminder_note or '').strip() or 'Follow-up reminder'
    return Reminder.objects.create(
        inquiry_type=inquiry_type,
        inquiry_id=inquiry.id,
        customer_name=inquiry.name,
        mobile_number=inquiry.mobile,
        reminder_date=inquiry.reminder_date,
        reminder_time=inquiry.reminder_time,
        note=note,
        created_by=created_by or getattr(inquiry, 'created_by', None),
        status=Reminder.ReminderStatus.PENDING,
    )


def sync_booking_reminder(
    jobcard: JobCard,
    *,
    created_by: Optional[User] = None,
) -> Optional[Reminder]:
    """
    Mirror a booking's reminder fields into the unified Reminder table.

    Every `booking` row is owned by this function, because there is no
    equivalent of the inquiry pages' Reminder button for bookings. That makes
    it safe to reconcile rather than only ever insert: editing a booking moves
    its existing row instead of leaving a stale duplicate behind, which is a
    real flow here since Edit Booking exposes the reminder fields.

    The inquiry sync above deliberately keeps its insert-only behaviour, since
    staff can create inquiry reminders by hand and those are indistinguishable
    from synced ones.
    """
    pending = Reminder.objects.filter(
        inquiry_type=Reminder.InquiryType.BOOKING,
        inquiry_id=jobcard.id,
        status=Reminder.ReminderStatus.PENDING,
    )

    if jobcard.is_reminder_done:
        # Handled by staff: keep it as history rather than dropping it.
        pending.update(status=Reminder.ReminderStatus.COMPLETED)
        return None

    if not jobcard.reminder_date:
        # The reminder was cleared, so it should stop being outstanding.
        pending.delete()
        return None

    client = getattr(jobcard, 'client', None)
    values = {
        'customer_name': (getattr(client, 'full_name', '') or 'Customer')[:255],
        'mobile_number': _mobile_for_reminder(getattr(client, 'mobile', '')),
        'reminder_date': jobcard.reminder_date,
        'reminder_time': jobcard.reminder_time,
        'note': (jobcard.reminder_note or '').strip() or 'Booking follow-up',
    }

    existing = pending.order_by('id').first()
    if existing:
        for field, value in values.items():
            setattr(existing, field, value)
        existing.save(update_fields=[*values, 'updated_at'])
        return existing

    return Reminder.objects.create(
        inquiry_type=Reminder.InquiryType.BOOKING,
        inquiry_id=jobcard.id,
        created_by=created_by or getattr(jobcard, 'created_by', None),
        status=Reminder.ReminderStatus.PENDING,
        **values,
    )


def backfill_legacy_reminders() -> int:
    """Migrate pending legacy reminders into the unified Reminder table."""
    created = 0

    for inquiry in CRMInquiry.objects.filter(
        reminder_date__isnull=False,
        is_reminder_done=False,
    ).iterator():
        if sync_legacy_reminder_for_inquiry(
            inquiry,
            Reminder.InquiryType.CRM,
            created_by=inquiry.created_by,
        ):
            created += 1

    for inquiry in Inquiry.objects.filter(
        reminder_date__isnull=False,
        is_reminder_done=False,
    ).iterator():
        if sync_legacy_reminder_for_inquiry(
            inquiry,
            Reminder.InquiryType.WEBSITE,
            created_by=inquiry.created_by,
        ):
            created += 1

    for jobcard in JobCard.objects.filter(
        reminder_date__isnull=False,
        is_reminder_done=False,
    ).select_related('client').iterator():
        if sync_booking_reminder(jobcard, created_by=jobcard.created_by):
            created += 1

    return created


def push_booking_reminder_back(reminder: Reminder) -> None:
    """
    Copy an edited booking reminder back onto its booking.

    The booking is the source of truth for the mirror, so without this an edit
    made on the Reminders tab would be silently undone the next time anyone
    saved that booking.
    """
    if reminder.inquiry_type != Reminder.InquiryType.BOOKING:
        return

    # .update() skips post_save, so this does not re-enter the booking signal.
    JobCard.objects.filter(id=reminder.inquiry_id).update(
        reminder_date=reminder.reminder_date,
        reminder_time=reminder.reminder_time,
        reminder_note=reminder.note,
        is_reminder_done=reminder.status == Reminder.ReminderStatus.COMPLETED,
    )


def mark_source_inquiry_reminder_done(reminder: Reminder) -> None:
    """Mark legacy reminder fields done on the linked inquiry, if applicable."""
    if reminder.inquiry_type == Reminder.InquiryType.CRM:
        CRMInquiry.objects.filter(
            id=reminder.inquiry_id,
            reminder_date=reminder.reminder_date,
            is_reminder_done=False,
        ).update(is_reminder_done=True)
    elif reminder.inquiry_type == Reminder.InquiryType.WEBSITE:
        Inquiry.objects.filter(
            id=reminder.inquiry_id,
            reminder_date=reminder.reminder_date,
            is_reminder_done=False,
        ).update(is_reminder_done=True)
    elif reminder.inquiry_type == Reminder.InquiryType.BOOKING:
        # .update() skips post_save, so this cannot bounce back through the
        # booking signal and re-open the reminder it just closed.
        JobCard.objects.filter(
            id=reminder.inquiry_id,
            reminder_date=reminder.reminder_date,
            is_reminder_done=False,
        ).update(is_reminder_done=True)
