from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_inquiry_estimated_price_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='crminquiry',
            name='service_frequency',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Website-style plan: one-time or amc',
                max_length=50,
                null=True,
                verbose_name='Service Frequency',
            ),
        ),
    ]
