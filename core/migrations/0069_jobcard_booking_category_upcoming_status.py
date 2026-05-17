# Generated manually for service-call workflow separation

from django.db import migrations, models


def sync_categories_and_upcoming_status(apps, schema_editor):
    JobCard = apps.get_model('core', 'JobCard')

    for job in JobCard.objects.all().iterator(chunk_size=500):
        # Mirror JobCard.sync_booking_category logic
        if job.is_complaint_call or job.booking_type == 'Complaint Call':
            category = 'complaint_call'
        elif job.booking_type == 'AMC Follow-up' or (job.is_followup_visit and job.included_in_amc):
            category = 'amc_followup'
        elif job.is_service_call or job.booking_type == 'Service Call' or (job.service_cycle or 1) > 1:
            category = 'service_call'
        else:
            category = 'normal_booking'

        updates = {'booking_category': category}

        if category in ('service_call', 'amc_followup') and job.status == 'Pending':
            updates['status'] = 'Upcoming'

        JobCard.objects.filter(pk=job.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0068_jobcard_unique_amc_cycle_per_parent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobcard',
            name='status',
            field=models.CharField(
                choices=[
                    ('Upcoming', 'Upcoming'),
                    ('Pending', 'Pending'),
                    ('On Process', 'On Process'),
                    ('Done', 'Done'),
                    ('Cancelled', 'Cancelled'),
                ],
                db_index=True,
                default='Pending',
                help_text='Current status of the job card',
                max_length=20,
                verbose_name='Status',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='booking_category',
            field=models.CharField(
                choices=[
                    ('normal_booking', 'Normal Booking'),
                    ('service_call', 'Service Call'),
                    ('complaint_call', 'Complaint Call'),
                    ('amc_followup', 'AMC Follow-up'),
                ],
                db_index=True,
                default='normal_booking',
                help_text='Operational category: drives Pending vs Upcoming Services tabs',
                max_length=30,
                verbose_name='Booking Category',
            ),
        ),
        migrations.RunPython(sync_categories_and_upcoming_status, migrations.RunPython.noop),
    ]
