# Generated manually for Quotation GST fields.

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0103_pricingrate_gst_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='quotation',
            name='gst_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('18.00'),
                help_text='GST percentage applied to this quotation (e.g. 18.00)',
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='quotation',
            name='price_includes_gst',
            field=models.BooleanField(
                default=True,
                help_text='When True, line totals include GST; when False, GST is added after discount',
            ),
        ),
    ]
