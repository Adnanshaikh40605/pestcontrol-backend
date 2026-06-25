from django.db import migrations
from django.db.models import F


def backfill_completed_at(apps, schema_editor):
    JobCard = apps.get_model('core', 'JobCard')
    JobCard.objects.filter(
        status='Done',
        completed_at__isnull=True,
    ).update(completed_at=F('updated_at'))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0083_commercial_area_pricing'),
    ]

    operations = [
        migrations.RunPython(backfill_completed_at, migrations.RunPython.noop),
    ]
