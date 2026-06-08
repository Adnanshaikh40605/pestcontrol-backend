from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0078_pricing_master'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobcard',
            name='bhk_size',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Property size label (BHK, sq.ft. slab, commercial, etc.)',
                max_length=100,
                null=True,
                verbose_name='BHK / Area Size',
            ),
        ),
    ]
