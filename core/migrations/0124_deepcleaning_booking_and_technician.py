# Deep Cleaning bookings and technicians, kept separate from pest job cards.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0123_deepcleaning_rate'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeepCleaningTechnician',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('mobile', models.CharField(db_index=True, max_length=10, unique=True, validators=[core.validators.validate_mobile_number])),
                ('age', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('alternative_mobile', models.CharField(blank=True, max_length=10, null=True, validators=[core.validators.validate_mobile_number])),
                ('address', models.TextField(blank=True, default='')),
                ('location', models.CharField(blank=True, default='', max_length=255)),
                ('cities', models.JSONField(blank=True, default=list)),
                ('services', models.JSONField(blank=True, default=list)),
                ('presence_status', models.CharField(choices=[('active', 'Active'), ('on_leave', 'On Leave'), ('suspended', 'Suspended')], db_index=True, default='active', max_length=20)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'verbose_name': 'DeepCleaning99 Technician',
                'verbose_name_plural': 'DeepCleaning99 Technicians',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DeepCleaningBooking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('code', models.CharField(blank=True, db_index=True, max_length=20, unique=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('mobile', models.CharField(db_index=True, max_length=10, validators=[core.validators.validate_mobile_number])),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('city', models.CharField(db_index=True, default='Mumbai', max_length=100)),
                ('area', models.CharField(blank=True, default='', max_length=150)),
                ('address', models.TextField(blank=True, default='')),
                ('segment', models.CharField(blank=True, default='Residential', max_length=50)),
                ('service', models.CharField(db_index=True, max_length=255)),
                ('package_name', models.CharField(blank=True, default='', max_length=255)),
                ('package_id', models.CharField(blank=True, default='', max_length=50)),
                ('quantity', models.CharField(blank=True, default='', max_length=50)),
                ('unit', models.CharField(blank=True, default='', max_length=50)),
                ('plan', models.CharField(blank=True, default='one', max_length=50)),
                ('property_size', models.CharField(blank=True, default='', max_length=50)),
                ('property_type', models.CharField(blank=True, default='', max_length=50)),
                ('preferred_date', models.DateField(blank=True, db_index=True, null=True)),
                ('preferred_time', models.CharField(blank=True, default='', max_length=100)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[core.validators.validate_non_negative_decimal])),
                ('notes', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('On Process', 'On Process'), ('Done', 'Done'), ('Cancelled', 'Cancelled')], db_index=True, default='Pending', max_length=20)),
                ('assigned_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deepcleaning_bookings', to=settings.AUTH_USER_MODEL)),
                ('inquiry', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='booking', to='core.deepcleaninginquiry')),
                ('technician', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookings', to='core.deepcleaningtechnician')),
            ],
            options={
                'verbose_name': 'DeepCleaning99 Booking',
                'verbose_name_plural': 'DeepCleaning99 Bookings',
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
