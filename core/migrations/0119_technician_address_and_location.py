# Technician home/base address. Blank defaults keep existing rows valid.
# Service areas (service_cities) are unchanged and still drive job filtering.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0118_technician_service_eligibility'),
    ]

    operations = [
        migrations.AddField(
            model_name='technician',
            name='address',
            field=models.TextField(
                blank=True,
                default='',
                help_text=(
                    'Full address where this technician lives or works from. '
                    'Existing rows stay blank. Not used for job filtering.'
                ),
                verbose_name='Address',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='location',
            field=models.CharField(
                blank=True,
                default='',
                help_text=(
                    'City and area where this technician is based, such as Baner, Pune. '
                    'Separate from service areas used for job filtering.'
                ),
                max_length=255,
                verbose_name='Location',
            ),
        ),
    ]
