"""
Allow a Reminder to point at a booking, and mirror the bookings that already
have a reminder set.

Hand-written because `makemigrations` cannot serialise an unrelated lru_cache
default elsewhere in core.models; the other recent core migrations are written
the same way for the same reason.
"""
from django.db import migrations, models


def mirror_existing_booking_reminders(apps, schema_editor):
    """
    Bookings saved before this change have reminder fields that never reached
    the Reminders tab. Bring the outstanding ones across so staff see the
    follow-ups they already recorded.
    """
    JobCard = apps.get_model('core', 'JobCard')
    Reminder = apps.get_model('core', 'Reminder')

    bookings = (
        JobCard.objects
        .filter(reminder_date__isnull=False, is_reminder_done=False)
        .select_related('client')
    )

    for booking in bookings.iterator():
        already_mirrored = Reminder.objects.filter(
            inquiry_type='booking',
            inquiry_id=booking.id,
            status='pending',
        ).exists()
        if already_mirrored:
            continue

        client = booking.client
        mobile = ''.join(ch for ch in (getattr(client, 'mobile', '') or '') if ch.isdigit())

        Reminder.objects.create(
            inquiry_type='booking',
            inquiry_id=booking.id,
            customer_name=(getattr(client, 'full_name', '') or 'Customer')[:255],
            mobile_number=mobile[-10:],
            reminder_date=booking.reminder_date,
            reminder_time=booking.reminder_time,
            note=(booking.reminder_note or '').strip() or 'Booking follow-up',
            created_by=booking.created_by,
            status='pending',
        )


def drop_mirrored_booking_reminders(apps, schema_editor):
    """Reverse: booking reminders cannot be represented once the choice is gone."""
    Reminder = apps.get_model('core', 'Reminder')
    Reminder.objects.filter(inquiry_type='booking').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0111_technician_status_and_remarks'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reminder',
            name='inquiry_type',
            field=models.CharField(
                choices=[
                    ('crm', 'CRM Inquiry'),
                    ('website', 'Website Inquiry'),
                    ('booking', 'Booking'),
                ],
                db_index=True,
                max_length=20,
                verbose_name='Inquiry Type',
            ),
        ),
        migrations.RunPython(
            mirror_existing_booking_reminders,
            drop_mirrored_booking_reminders,
        ),
    ]
