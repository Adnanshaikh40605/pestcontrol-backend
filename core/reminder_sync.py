"""
Sync legacy inquiry/booking reminder fields into the unified Reminder table.
"""
from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import User

from .models import CRMInquiry, Inquiry, Reminder


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

    return created


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
