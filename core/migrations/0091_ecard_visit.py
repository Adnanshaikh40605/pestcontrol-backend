from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0090_booking_report_client_city'),
    ]

    operations = [
        migrations.CreateModel(
            name='ECardVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('city', models.CharField(blank=True, db_index=True, default='Unknown', max_length=100)),
                ('device_type', models.CharField(choices=[('Mobile', 'Mobile'), ('Desktop', 'Desktop'), ('Tablet', 'Tablet')], db_index=True, default='Desktop', max_length=20)),
                ('traffic_source', models.CharField(choices=[('Google Search', 'Google Search'), ('Facebook', 'Facebook'), ('Instagram', 'Instagram'), ('WhatsApp', 'WhatsApp'), ('YouTube', 'YouTube'), ('LinkedIn', 'LinkedIn'), ('Email', 'Email'), ('Direct Link', 'Direct Link'), ('Another Website (Referral)', 'Another Website (Referral)')], db_index=True, default='Direct Link', max_length=40)),
                ('visited_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('ip_address', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('user_agent', models.CharField(blank=True, default='', max_length=512)),
                ('referrer', models.CharField(blank=True, default='', max_length=500)),
            ],
            options={
                'verbose_name': 'E-Card Visit',
                'verbose_name_plural': 'E-Card Visits',
                'ordering': ['-visited_at', '-id'],
                'indexes': [
                    models.Index(fields=['-visited_at'], name='core_ecardv_visited_idx'),
                    models.Index(fields=['traffic_source', '-visited_at'], name='core_ecardv_traffic_idx'),
                    models.Index(fields=['device_type', '-visited_at'], name='core_ecardv_device_idx'),
                    models.Index(fields=['city', '-visited_at'], name='core_ecardv_city_idx'),
                ],
            },
        ),
    ]
