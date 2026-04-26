from django.db import migrations


STATUS_REMAP = {
    # Old           # New
    'Completed':    'Done',
    'WIP':          'On Process',
    'Hold':         'On Process',
    'Confirmed':    'On Process',
    'In Progress':  'On Process',
    'Enquiry':      'Pending',
    'Inactive':     'Pending',
    'Cancel':       'Pending',
    'Cancelled':    'Pending',
    'New':          'Pending',
}


def migrate_statuses_forward(apps, schema_editor):
    JobCard = apps.get_model('core', 'JobCard')
    for old_status, new_status in STATUS_REMAP.items():
        updated = JobCard.objects.filter(status=old_status).update(status=new_status)
        if updated:
            print(f"  Migrated {updated} records: '{old_status}' -> '{new_status}'")


def migrate_statuses_backward(apps, schema_editor):
    # Non-reversible - can't reliably undo a many-to-one mapping
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_alter_jobcard_status_alter_jobcard_time_slot'),
    ]

    operations = [
        migrations.RunPython(migrate_statuses_forward, migrate_statuses_backward),
    ]
