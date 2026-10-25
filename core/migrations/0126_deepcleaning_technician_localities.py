# Localities a Deep Cleaning technician covers, stored with the city.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0125_deepcleaning_inquiry_booking_session'),
    ]

    operations = [
        migrations.AddField(
            model_name='deepcleaningtechnician',
            name='localities',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Areas this technician covers, as {"city", "name"} objects.',
            ),
        ),
    ]
