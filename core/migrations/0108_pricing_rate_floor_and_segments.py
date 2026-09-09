"""Room for the 2026 master rate chart: an internal floor, a billing basis and
the property segments it prices separately (society, hospital, hotel, corporate,
multi-site, add-ons).

Hand-written because `makemigrations` cannot serialize the lru_cache-wrapped
storage callable on an unrelated core FileField.
"""
from decimal import Decimal

from django.db import migrations, models

CATEGORY_CHOICES = [
    ('residential', 'Residential (BHK/RK)'),
    ('villa', 'Villa / Bungalow (Sq.Ft.)'),
    ('fogging', 'Fogging (Sq.Ft.)'),
    ('rodent', 'Rodent / Reptile'),
    ('commercial', 'Commercial'),
    ('society', 'Housing Society (Common Area)'),
    ('hospital', 'Hospital / Clinic'),
    ('hotel', 'Hotel / Restaurant / Cloud Kitchen'),
    ('corporate', 'Corporate One-Time'),
    ('corporate_monthly', 'Corporate Monthly Contract'),
    ('multi_site', 'Multi-Site Chain (Per Outlet)'),
    ('addon', 'Add-On / Equipment / SLA'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0107_inquiry_staff_whatsapp_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricingrate',
            name='floor_amount',
            field=models.DecimalField(
                max_digits=10,
                decimal_places=2,
                null=True,
                blank=True,
                help_text=(
                    'Internal lowest acceptable rate for negotiation, on the same '
                    'GST basis as amount. Never expose this to customers.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='pricingrate',
            name='billing_basis',
            field=models.CharField(
                max_length=40,
                blank=True,
                default='',
                help_text=(
                    "How the rate is billed, e.g. 'Per month', 'Per room', "
                    "'Per outlet/month'."
                ),
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='pricingrate',
            name='property_category',
            field=models.CharField(
                max_length=20,
                choices=CATEGORY_CHOICES,
                default='residential',
                db_index=True,
            ),
        ),
    ]
