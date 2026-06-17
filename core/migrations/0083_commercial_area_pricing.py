from django.db import migrations


def add_commercial_area_rates(apps, schema_editor):
    from core.pricing.seed import ensure_commercial_area_rates

    ensure_commercial_area_rates()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0082_jobcard_service_items'),
    ]

    operations = [
        migrations.RunPython(add_commercial_area_rates, migrations.RunPython.noop),
    ]
