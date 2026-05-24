from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0075_userpreference'),
        ('partner', '0006_restore_partner_device_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerReferral',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_name', models.CharField(db_index=True, max_length=255)),
                ('mobile', models.CharField(db_index=True, max_length=10)),
                ('area', models.CharField(blank=True, default='', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'crm_inquiry',
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='partner_referral',
                        to='core.crminquiry',
                        verbose_name='CRM Inquiry',
                    ),
                ),
                (
                    'partner',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='referrals',
                        to='partner.partner',
                        verbose_name='Referred By (Partner)',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Partner Referral',
                'verbose_name_plural': 'Partner Referrals',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='partnerreferral',
            index=models.Index(fields=['partner', '-created_at'], name='partner_par_partner_8f3a21_idx'),
        ),
    ]
