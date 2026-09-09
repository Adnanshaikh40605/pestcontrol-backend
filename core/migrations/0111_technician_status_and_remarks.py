"""Collapse presence_status to three work statuses, and add technician remarks.

presence_status carried six values that mixed two different ideas: a work
status the CRM desk chose (on_leave, suspended) and live app presence the job
lifecycle wrote (online, offline, busy, on_service). Accepting a job set
'busy', so whatever the desk had selected was silently overwritten. It is now
one thing only - Active / On Leave / Suspended - and the lifecycle writes are
gone.

The four runtime values all map to 'active': none of them ever blocked a
broadcast, a push, an assignment or a payout, so an 'offline' technician was
already a working technician whose app happened to be shut.

Hand-written because `makemigrations` cannot serialize the lru_cache-wrapped
storage callable on Partner.profile_image. Choices are inlined in full (as in
0094, which added this field), so changing the enum means repeating the list.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


PRESENCE_CHOICES = [
    ('active', 'Active'),
    ('on_leave', 'On Leave'),
    ('suspended', 'Suspended'),
]

PRESENCE_HELP = 'Active, On Leave or Suspended. Set by the CRM desk.'

# Everything that was live-presence rather than a work decision becomes Active.
RETIRED_TO_ACTIVE = ['online', 'offline', 'busy', 'on_service']


def collapse_presence(apps, schema_editor):
    Technician = apps.get_model('core', 'Technician')
    Technician.objects.filter(presence_status__in=RETIRED_TO_ACTIVE).update(
        presence_status='active',
    )
    # Any value outside the new enum (older rows, manual edits) is not left
    # dangling: an unreadable status must not silently gate dispatch.
    Technician.objects.exclude(
        presence_status__in=['active', 'on_leave', 'suspended'],
    ).update(presence_status='active')


def restore_presence(apps, schema_editor):
    """Reverse: 'active' becomes 'offline', the old default.

    The original online/busy/on_service distinctions are not recoverable -
    they were transient runtime state, not stored history.
    """
    Technician = apps.get_model('core', 'Technician')
    Technician.objects.filter(presence_status='active').update(
        presence_status='offline',
    )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0110_pricing_category_labels'),
    ]

    operations = [
        migrations.RunPython(collapse_presence, restore_presence),
        migrations.AlterField(
            model_name='technician',
            name='presence_status',
            field=models.CharField(
                choices=PRESENCE_CHOICES,
                db_index=True,
                default='active',
                help_text=PRESENCE_HELP,
                max_length=20,
                verbose_name='Presence Status',
            ),
        ),
        migrations.CreateModel(
            name='TechnicianRemark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('remark', models.TextField()),
                ('remark_date', models.DateField(
                    db_index=True,
                    help_text='Date the remark refers to, not necessarily when it was written.',
                )),
                ('remark_time', models.TimeField(help_text='Time the remark refers to.')),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='technician_remarks',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('technician', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='remarks',
                    to='core.technician',
                )),
            ],
            options={
                'verbose_name': 'Technician Remark',
                'verbose_name_plural': 'Technician Remarks',
                'ordering': ['-remark_date', '-remark_time', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='technicianremark',
            index=models.Index(
                fields=['technician', '-remark_date'],
                name='core_techni_technic_aff751_idx',
            ),
        ),
    ]
