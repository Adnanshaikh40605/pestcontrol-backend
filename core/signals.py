from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import UserProfile, CRMRole, CRMInquiry, Inquiry, JobCard, Reminder
from .reminder_sync import (
    BOOKING_REMINDER_FIELDS,
    sync_booking_reminder,
    sync_legacy_reminder_for_inquiry,
)

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_crm_profile(sender, instance, created, **kwargs):
    """Auto-create profile for new users; sync legacy superuser/staff flags."""
    if created:
        if instance.is_superuser:
            role = CRMRole.SUPER_ADMIN
        elif instance.is_staff:
            role = CRMRole.STAFF
        else:
            role = CRMRole.STAFF
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    elif not hasattr(instance, 'crm_profile'):
        if instance.is_superuser:
            UserProfile.objects.create(user=instance, role=CRMRole.SUPER_ADMIN)
        elif instance.is_staff:
            UserProfile.objects.create(user=instance, role=CRMRole.STAFF)


@receiver(post_save, sender=CRMInquiry)
def sync_crm_inquiry_reminder(sender, instance, **kwargs):
    if instance.reminder_date and not instance.is_reminder_done:
        sync_legacy_reminder_for_inquiry(
            instance,
            Reminder.InquiryType.CRM,
            created_by=instance.created_by,
        )


@receiver(post_save, sender=Inquiry)
def sync_website_inquiry_reminder(sender, instance, **kwargs):
    if instance.reminder_date and not instance.is_reminder_done:
        sync_legacy_reminder_for_inquiry(
            instance,
            Reminder.InquiryType.WEBSITE,
            created_by=instance.created_by,
        )


@receiver(post_save, sender=JobCard)
def sync_booking_reminder_row(sender, instance, update_fields=None, **kwargs):
    """
    Keep the Reminders tab in step with a booking's reminder fields.

    This runs unconditionally rather than only when a date is present, because
    clearing a reminder has to remove the mirrored row too. Bookings are saved
    often, so partial saves that cannot have touched a reminder skip the work.
    """
    if update_fields is not None and not BOOKING_REMINDER_FIELDS & set(update_fields):
        return
    sync_booking_reminder(instance, created_by=instance.created_by)


@receiver(post_delete, sender=JobCard)
def drop_booking_reminder_row(sender, instance, **kwargs):
    """
    Reminder links to its source by a plain id rather than a foreign key, so a
    deleted booking would otherwise leave a reminder on the tab pointing at a
    booking that no longer opens.
    """
    Reminder.objects.filter(
        inquiry_type=Reminder.InquiryType.BOOKING,
        inquiry_id=instance.id,
    ).delete()
