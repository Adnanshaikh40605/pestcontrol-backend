from django.db import migrations, models


def seed_customer_version(apps, schema_editor):
    CustomerAppVersionConfig = apps.get_model('core', 'CustomerAppVersionConfig')
    CustomerAppVersionConfig.objects.get_or_create(
        pk=1,
        defaults={
            'latest_version': '1.0.4',
            'minimum_supported_version': '1.0.4',
            'force_update': False,
            'update_title': 'Update required',
            'update_message': (
                'A new version of Pest Control 99 is available. Please update to continue.'
            ),
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0098_partnerappversionconfig'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerAppVersionConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latest_version', models.CharField(default='1.0.4', help_text='Latest Play Store version (e.g. 1.0.4)', max_length=20)),
                ('minimum_supported_version', models.CharField(default='1.0.4', help_text='Oldest app version allowed when force update is enabled', max_length=20)),
                ('force_update', models.BooleanField(default=False, help_text='When enabled, apps below minimum_supported_version (and latest) are blocked')),
                ('update_title', models.CharField(default='Update required', max_length=120)),
                ('update_message', models.TextField(default='A new version of Pest Control 99 is available. Please update to continue.')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Customer App Version',
                'verbose_name_plural': 'Customer App Version',
            },
        ),
        migrations.RunPython(seed_customer_version, migrations.RunPython.noop),
    ]
