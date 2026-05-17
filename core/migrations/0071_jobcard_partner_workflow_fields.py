from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0070_userprofile_crm_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='sent_to_app_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When CRM dispatched this booking to the partner mobile app',
                null=True,
                verbose_name='Sent To Partner App At',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='job_start_selfie',
            field=models.ImageField(
                blank=True,
                help_text='Selfie captured by technician when starting service',
                null=True,
                upload_to='job_selfies/%Y/%m/',
                verbose_name='Job Start Selfie',
            ),
        ),
    ]
