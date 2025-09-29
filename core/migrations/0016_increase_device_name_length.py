# Generated manually to fix device_name field length

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_simplify_notification_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devicetoken',
            name='device_name',
            field=models.CharField(blank=True, help_text='Optional name to identify the device (e.g., \'Admin Phone\')', max_length=255, null=True, verbose_name='Device Name'),
        ),
    ]
