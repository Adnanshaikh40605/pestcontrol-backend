# Generated manually for Pricing Master GST fields.

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0102_remove_app_version_configs'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricingrate',
            name='gst_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('18.00'),
                help_text='GST percentage applied to this rate (e.g. 18.00)',
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='pricingrate',
            name='price_includes_gst',
            field=models.BooleanField(
                default=True,
                help_text='When True, amount already includes GST; when False, GST is added on top',
            ),
        ),
    ]
