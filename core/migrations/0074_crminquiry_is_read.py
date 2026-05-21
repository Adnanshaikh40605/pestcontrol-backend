# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0073_inquiry_remarks'),
    ]

    operations = [
        migrations.AddField(
            model_name='crminquiry',
            name='is_read',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Staff has reviewed this CRM inquiry in the CRM',
                verbose_name='Is Read',
            ),
        ),
        migrations.AddIndex(
            model_name='crminquiry',
            index=models.Index(fields=['is_read', 'status'], name='core_crminq_is_read_8a1f2b_idx'),
        ),
    ]
