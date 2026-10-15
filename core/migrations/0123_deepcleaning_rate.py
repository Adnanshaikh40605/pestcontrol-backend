# DeepCleaning99 master price list, seeded from the Oct 2026 rate sheet.

import json
from decimal import Decimal
from pathlib import Path

from django.db import migrations, models


def seed_deepcleaning_rates(apps, schema_editor):
    Rate = apps.get_model('core', 'DeepCleaningRate')
    path = Path(__file__).resolve().parent.parent / 'data' / 'deepcleaning_launch_rates.json'
    rows = json.loads(path.read_text())
    money = (
        'example_qty',
        'rate_per_unit',
        'min_charge',
        'job_amount',
        'amc_discount',
        'amc_per_visit',
        'amc_annual',
    )
    for row in rows:
        payload = dict(row)
        payload['is_active'] = True
        for key in money:
            payload[key] = Decimal(str(payload[key]))
        Rate.objects.update_or_create(code=payload.pop('code'), defaults=payload)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0122_deepcleaning_inquiry'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeepCleaningRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('code', models.CharField(db_index=True, max_length=20, unique=True)),
                ('segment', models.CharField(choices=[('Residential', 'Residential'), ('Commercial', 'Commercial')], db_index=True, max_length=20)),
                ('service', models.CharField(db_index=True, max_length=120)),
                ('package_name', models.CharField(max_length=255)),
                ('billing_unit', models.CharField(default='package', max_length=40)),
                ('example_qty', models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ('rate_per_unit', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('min_charge', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('job_amount', models.DecimalField(decimal_places=2, default=0, help_text='One-time list price before the website offer. GST extra.', max_digits=12)),
                ('technicians', models.PositiveIntegerField(default=1)),
                ('on_site_hours', models.CharField(blank=True, default='', max_length=40)),
                ('scope_note', models.TextField(blank=True, default='')),
                ('amc_visits', models.PositiveIntegerField(default=0)),
                ('amc_discount', models.DecimalField(decimal_places=4, default=0, max_digits=5)),
                ('amc_per_visit', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('amc_annual', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('amc_interval', models.CharField(blank=True, default='', max_length=40)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'DeepCleaning99 Rate',
                'verbose_name_plural': 'DeepCleaning99 Rates',
                'ordering': ['sort_order', 'code'],
            },
        ),
        migrations.RunPython(seed_deepcleaning_rates, migrations.RunPython.noop),
    ]
