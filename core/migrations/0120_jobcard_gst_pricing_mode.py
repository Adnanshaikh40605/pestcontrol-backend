# Booking GST pricing mode. Existing rows keep their stored price; the new
# amount columns stay null until a booking is saved with a GST mode.

from decimal import Decimal

from django.db import migrations, models

import core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0119_technician_address_and_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='gst_mode',
            field=models.CharField(
                choices=[
                    ('GST_INCLUSIVE', 'GST Inclusive'),
                    ('GST_EXCLUSIVE', 'GST Exclusive'),
                ],
                default='GST_INCLUSIVE',
                help_text='GST Inclusive keeps the entered price as the customer total. GST Exclusive adds GST on top.',
                max_length=20,
                verbose_name='GST Pricing Mode',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='gst_rate',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('18.00'),
                max_digits=5,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='GST Rate',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='original_service_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Entered service price after discount, before the GST mode is applied.',
                max_digits=12,
                null=True,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Original Service Price',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='taxable_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Taxable Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='gst_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='GST Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='final_payable_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Final Customer Payable',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='overridden_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Staff booking-level price when it differs from the sum of service lines.',
                max_digits=12,
                null=True,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Overridden Price',
            ),
        ),
    ]
