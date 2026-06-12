from django.db import migrations


def backfill_reminders(apps, schema_editor):
    from core.reminder_sync import backfill_legacy_reminders

    backfill_legacy_reminders()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0079_jobcard_bhk_size_flexible'),
    ]

    operations = [
        migrations.RunPython(backfill_reminders, migrations.RunPython.noop),
    ]
