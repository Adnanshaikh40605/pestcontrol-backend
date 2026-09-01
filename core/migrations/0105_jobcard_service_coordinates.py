from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0104_quotation_gst_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='service_latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name='Service Latitude',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='service_longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name='Service Longitude',
            ),
        ),
    ]
