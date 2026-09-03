from django.db import migrations, transaction


def backfill_reminders(apps, schema_editor):
    """
    Historical data migration. Soft-fail if the live Inquiry model has columns
    that do not exist yet at this point in the migration graph (fresh test DBs).
    """
    try:
        with transaction.atomic():
            from core.reminder_sync import backfill_legacy_reminders

            backfill_legacy_reminders()
    except Exception:
        # Live model may already include later fields (e.g. staff_whatsapp_*).
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0079_jobcard_bhk_size_flexible'),
    ]

    operations = [
        migrations.RunPython(backfill_reminders, migrations.RunPython.noop),
    ]
