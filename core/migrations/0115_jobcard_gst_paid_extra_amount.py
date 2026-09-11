# Done Service: GST Paid + Extra Amount flags on JobCard.

from decimal import Decimal

from django.db import migrations, models

import core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0114_invoice_customer_gst_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='gst_paid',
            field=models.BooleanField(
                blank=True,
                db_index=True,
                help_text=(
                    'Whether the customer paid GST on completion. '
                    'True = amount includes GST; False = customer paid base only; '
                    'null = not recorded (legacy).'
                ),
                null=True,
                verbose_name='GST Paid',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='has_extra_amount',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Whether an extra amount was collected at Done Service '
                    '(only when GST Paid).'
                ),
                verbose_name='Has Extra Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='extra_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text=(
                    'Extra rupees collected at Done Service when has_extra_amount is True.'
                ),
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Extra Amount',
            ),
        ),
    ]
