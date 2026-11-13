from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0129_hide_conflicting_deepcleaning_rates'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inquiry',
            name='status',
            field=models.CharField(
                choices=[
                    ('New', 'New'),
                    ('Inspection Requested', 'Inspection Requested'),
                    ('Contacted', 'Contacted'),
                    ('Converted', 'Converted'),
                    ('Closed', 'Closed'),
                ],
                db_index=True,
                default='New',
                help_text='Current status of the inquiry',
                max_length=32,
                verbose_name='Status',
            ),
        ),
    ]
