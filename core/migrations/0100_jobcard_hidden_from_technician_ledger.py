# Generated manually for technician ledger booking actions.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0099_customerappversionconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='hidden_from_technician_ledger',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='When True, staff removed this booking from the technician ledger UI. Booking remains in CRM.',
                verbose_name='Hidden From Technician Ledger',
            ),
        ),
    ]
