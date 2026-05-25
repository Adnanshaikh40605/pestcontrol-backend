from django.db import migrations, models


def seed_version_config(apps, schema_editor):
    PartnerAppVersionConfig = apps.get_model('core', 'PartnerAppVersionConfig')
    PartnerAppVersionConfig.objects.get_or_create(
        pk=1,
        defaults={
            'latest_version': '2.0.0',
            'minimum_supported_version': '0.1.0',
            'force_update': False,
            'update_title': 'New Update Available',
            'update_message': (
                'A new version of the Partner App is available. '
                'Please uninstall the old app and install the latest APK shared by the company.'
            ),
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0075_userpreference'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerAppVersionConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'latest_version',
                    models.CharField(
                        default='2.0.0',
                        help_text='Latest APK version released by the company (e.g. 2.0.0)',
                        max_length=20,
                    ),
                ),
                (
                    'minimum_supported_version',
                    models.CharField(
                        default='0.1.0',
                        help_text='Oldest app version allowed to run when force update is enabled',
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
                ('update_title', models.CharField(default='New Update Available', max_length=120)),
                (
                    'update_message',
                    models.TextField(
                        default=(
                            'A new version of the Partner App is available. '
                            'Please uninstall the old app and install the latest APK shared by the company.'
                        ),
                    ),
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
