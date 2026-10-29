# Hide residential rates that are not on the Diwali 2026 sheet.

import json
from pathlib import Path

from django.db import migrations


def hide_rates_outside_diwali_sheet(apps, schema_editor):
    Rate = apps.get_model('core', 'DeepCleaningRate')
    path = Path(__file__).resolve().parent.parent / 'data' / 'deepcleaning_diwali_rates_2026.json'
    official = {row['code'] for row in json.loads(path.read_text())}
    kept = {'R29', *[f'C{index}' for index in range(1, 18)]}
    Rate.objects.filter(is_active=True).exclude(code__in=official | kept).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0128_technician_finished_stays_on_process'),
    ]

    operations = [
        migrations.RunPython(hide_rates_outside_diwali_sheet, migrations.RunPython.noop),
    ]
