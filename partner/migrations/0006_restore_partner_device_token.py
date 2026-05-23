from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0005_remove_firebase_fcm'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerDeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fcm_token', models.CharField(db_index=True, max_length=512, unique=True)),
                ('device_type', models.CharField(
                    choices=[('android', 'Android'), ('ios', 'iOS')],
                    default='android',
                    max_length=20,
                )),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('last_used_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('partner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='device_tokens',
                    to='partner.partner',
                )),
            ],
            options={
                'verbose_name': 'Partner Device Token',
                'verbose_name_plural': 'Partner Device Tokens',
                'indexes': [
                    models.Index(fields=['partner', 'is_active'], name='partner_par_partner_5156c0_idx'),
                ],
            },
        ),
    ]
