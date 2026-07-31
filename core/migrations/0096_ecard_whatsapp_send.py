import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0095_technician_settlements'),
    ]

    operations = [
        migrations.CreateModel(
            name='ECardWhatsAppSend',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text='Date and time when the record was created',
                        verbose_name='Created At',
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text='Date and time when the record was last updated',
                        verbose_name='Updated At',
                    ),
                ),
                (
                    'mobile',
                    models.CharField(
                        db_index=True,
                        help_text='10-digit Indian mobile (normalized)',
                        max_length=10,
                        unique=True,
                        verbose_name='Mobile Number',
                    ),
                ),
                (
                    'template_name',
                    models.CharField(
                        db_index=True,
                        default='pestecardaadsd',
                        max_length=100,
                        verbose_name='Template Name',
                    ),
                ),
                ('customer_name', models.CharField(blank=True, default='', max_length=255)),
                (
                    'sent_by',
                    models.CharField(
                        blank=True,
                        default='',
                        help_text='Staff display name who sent the e-card',
                        max_length=255,
                        verbose_name='Sent By',
                    ),
                ),
                ('sent_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    'source',
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default='',
                        help_text='doh_crm | pest_crm | website_inquiry | crm_inquiry',
                        max_length=40,
                    ),
                ),
                (
                    'sent_by_user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ecard_whatsapp_sends',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Sent By User',
                    ),
                ),
            ],
            options={
                'verbose_name': 'E-Card WhatsApp Send',
                'verbose_name_plural': 'E-Card WhatsApp Sends',
                'ordering': ['-sent_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='ecardwhatsappsend',
            index=models.Index(fields=['-sent_at'], name='core_ecardw_sent_at_idx'),
        ),
    ]
