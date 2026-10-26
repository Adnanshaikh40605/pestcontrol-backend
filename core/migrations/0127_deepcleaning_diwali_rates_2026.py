# Publish the DeepCleaning99 Diwali 2026 residential selling rates.

import json
from decimal import Decimal
from pathlib import Path

from django.db import migrations


def load_diwali_rates(apps, schema_editor):
    Rate = apps.get_model('core', 'DeepCleaningRate')
    path = Path(__file__).resolve().parent.parent / 'data' / 'deepcleaning_diwali_rates_2026.json'
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

    # The previous residential sheet is replaced. Commercial rates and the
    # home-office rate stay, after the new residential list.
    Rate.objects.filter(code__in=[f'R{index}' for index in range(1, 29)]).update(is_active=False)
    kept = ['R29', *[f'C{index}' for index in range(1, 18)]]
    for offset, code in enumerate(kept):
        Rate.objects.filter(code=code).update(sort_order=1000 + offset)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0126_deepcleaning_technician_localities'),
    ]

    operations = [
        migrations.RunPython(load_diwali_rates, migrations.RunPython.noop),
    ]
