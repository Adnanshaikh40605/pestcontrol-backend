# Silent DeepCleaning99 lead capture, keyed by the browser booking session.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0124_deepcleaning_booking_and_technician'),
    ]

    operations = [
        migrations.AddField(
            model_name='deepcleaninginquiry',
            name='booking_session_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Browser session id from the DeepCleaning99 booking form (silent upsert key)',
                max_length=64,
                null=True,
            ),
        ),
    ]
