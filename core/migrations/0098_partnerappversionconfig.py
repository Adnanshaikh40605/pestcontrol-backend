from django.db import migrations, models


def seed_version_config(apps, schema_editor):
    PartnerAppVersionConfig = apps.get_model('core', 'PartnerAppVersionConfig')
    PartnerAppVersionConfig.objects.get_or_create(
        pk=1,
        defaults={
            'latest_version': '2.0.8',
            'minimum_supported_version': '2.0.8',
            'force_update': False,
            'update_title': 'Please update the app.',
            'update_message': 'Please update the app.',
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0097_delete_partnerappversionconfig'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerAppVersionConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'latest_version',
                    models.CharField(
                        default='2.0.8',
                        help_text='Latest Play Store version (e.g. 2.0.8)',
                        max_length=20,
                    ),
                ),
                (
                    'minimum_supported_version',
                    models.CharField(
                        default='2.0.8',
                        help_text='Oldest app version allowed when force update is enabled',
                        max_length=20,
                    ),
                ),
                (
                    'force_update',
                    models.BooleanField(
                        default=False,
                        help_text='When enabled, apps below minimum_supported_version are blocked',
                    ),
                ),
                ('update_title', models.CharField(default='Please update the app.', max_length=120)),
                (
                    'update_message',
                    models.TextField(default='Please update the app.'),
                ),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Partner App Version',
                'verbose_name_plural': 'Partner App Version',
            },
        ),
        migrations.RunPython(seed_version_config, migrations.RunPython.noop),
    ]
