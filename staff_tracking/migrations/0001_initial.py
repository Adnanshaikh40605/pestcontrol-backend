# Generated manually for staff_tracking initial schema

import django.db.models.deletion
import django.utils.timezone
from datetime import time
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0083_commercial_area_pricing'),
        ('partner', '0007_partner_referral'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TrackingSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('ping_interval_moving_seconds', models.PositiveIntegerField(default=30)),
                ('ping_interval_idle_seconds', models.PositiveIntegerField(default=300)),
                ('location_retention_days', models.PositiveIntegerField(default=90)),
                ('shift_start_time', models.TimeField(default=time(9, 0))),
                ('shift_end_time', models.TimeField(default=time(18, 0))),
                ('grace_minutes', models.PositiveIntegerField(default=15)),
            ],
            options={
                'verbose_name': 'Tracking Settings',
                'verbose_name_plural': 'Tracking Settings',
            },
        ),
        migrations.CreateModel(
            name='TrackingProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('tracking_enabled', models.BooleanField(db_index=True, default=True)),
                ('partner', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tracking_profile', to='partner.partner')),
                ('technician', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tracking_profile', to='core.technician')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tracking_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tracking Profile',
                'verbose_name_plural': 'Tracking Profiles',
            },
        ),
        migrations.CreateModel(
            name='TrackingConsent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('consented_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('consent_version', models.CharField(default='1.0', max_length=20)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='consent', to='staff_tracking.trackingprofile')),
            ],
            options={
                'verbose_name': 'Tracking Consent',
                'verbose_name_plural': 'Tracking Consents',
            },
        ),
        migrations.CreateModel(
            name='AttendanceSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('date', models.DateField(db_index=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed')], db_index=True, default='active', max_length=20)),
                ('check_in_at', models.DateTimeField()),
                ('check_out_at', models.DateTimeField(blank=True, null=True)),
                ('check_in_latitude', models.DecimalField(decimal_places=7, max_digits=10)),
                ('check_in_longitude', models.DecimalField(decimal_places=7, max_digits=10)),
                ('check_in_accuracy_m', models.FloatField(blank=True, null=True)),
                ('check_out_latitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ('check_out_longitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ('check_out_accuracy_m', models.FloatField(blank=True, null=True)),
                ('total_distance_km', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=8)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_sessions', to='staff_tracking.trackingprofile')),
            ],
            options={
                'verbose_name': 'Attendance Session',
                'verbose_name_plural': 'Attendance Sessions',
            },
        ),
        migrations.CreateModel(
            name='LocationPing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('latitude', models.DecimalField(decimal_places=7, max_digits=10)),
                ('longitude', models.DecimalField(decimal_places=7, max_digits=10)),
                ('accuracy_m', models.FloatField(blank=True, null=True)),
                ('altitude_m', models.FloatField(blank=True, null=True)),
                ('speed_mps', models.FloatField(blank=True, null=True)),
                ('heading', models.FloatField(blank=True, null=True)),
                ('battery_percent', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField(db_index=True)),
                ('is_moving', models.BooleanField(default=True)),
                ('attendance_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pings', to='staff_tracking.attendancesession')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='location_pings', to='staff_tracking.trackingprofile')),
            ],
            options={
                'verbose_name': 'Location Ping',
                'verbose_name_plural': 'Location Pings',
                'ordering': ['-recorded_at'],
            },
        ),
        migrations.AddIndex(
            model_name='attendancesession',
            index=models.Index(fields=['date', 'profile'], name='staff_track_date_6a8f2d_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancesession',
            index=models.Index(fields=['profile', '-check_in_at'], name='staff_track_profile_91c4e1_idx'),
        ),
        migrations.AddConstraint(
            model_name='attendancesession',
            constraint=models.UniqueConstraint(fields=('profile', 'date'), name='unique_attendance_per_profile_per_day'),
        ),
        migrations.AddIndex(
            model_name='locationping',
            index=models.Index(fields=['profile', '-recorded_at'], name='staff_track_profile_2b7a9f_idx'),
        ),
        migrations.AddIndex(
            model_name='locationping',
            index=models.Index(fields=['attendance_session', 'recorded_at'], name='staff_track_attenda_4c1d8e_idx'),
        ),
    ]
