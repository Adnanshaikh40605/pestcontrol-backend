# A technician-finished visit stays On Process until staff mark it Done.

from django.db import migrations


def move_finished_visits_to_on_process(apps, schema_editor):
    JobCard = apps.get_model('core', 'JobCard')
    JobCard.objects.filter(
        status='Pending',
        partner_status='completed',
    ).update(status='On Process')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0127_deepcleaning_diwali_rates_2026'),
    ]

    operations = [
        migrations.RunPython(
            move_finished_visits_to_on_process,
            migrations.RunPython.noop,
        ),
    ]
