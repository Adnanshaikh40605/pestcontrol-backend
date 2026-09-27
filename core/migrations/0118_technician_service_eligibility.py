# Existing technicians must keep every job. default=True on each AddField
# backfills current rows as One-Time + AMC + Standard + Premium.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0117_inquiry_booking_session_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='technician',
            name='accepts_one_time_jobs',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Eligible for One-Time Service bookings. '
                    'Existing technicians default to enabled.'
                ),
                verbose_name='One-Time Jobs',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='accepts_amc_jobs',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Eligible for AMC bookings. Existing technicians default to enabled.'
                ),
                verbose_name='AMC Jobs',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='accepts_standard_service',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Eligible for Standard treatment jobs (Cockroach Standard, and any '
                    'service that carries an explicit standard flag). '
                    'Existing technicians default to enabled.'
                ),
                verbose_name='Standard Service',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='accepts_premium_service',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Eligible for Premium treatment jobs (Cockroach Premium, and any '
                    'service that carries an explicit premium flag). '
                    'Existing technicians default to enabled.'
                ),
                verbose_name='Premium Service',
            ),
        ),
    ]
