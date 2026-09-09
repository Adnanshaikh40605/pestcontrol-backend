"""Relabel two pricing segments; stored values unchanged.

'fogging' and 'rodent' were labelled after the service they price ('Fogging
(Sq.Ft.)'), which read as a service name inside the Property category
dropdown. They now describe the area being priced. Display-only: no data
moves, so booking rate lookups are unaffected.

Hand-written because `makemigrations` cannot serialize the lru_cache-wrapped
storage callable on an unrelated core FileField.
"""

from django.db import migrations, models


PROPERTY_CATEGORY_CHOICES = [
    ('residential', 'Residential (BHK/RK)'),
    ('villa', 'Villa / Bungalow (Sq.Ft.)'),
    ('fogging', 'Open / Outdoor Area (Sq.Ft.)'),
    ('rodent', 'Rodent / Reptile Zone (Sq.Ft.)'),
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
        ('core', '0109_technician_secondary_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricingrate',
            name='property_category',
            field=models.CharField(
                choices=PROPERTY_CATEGORY_CHOICES,
                db_index=True,
                default='residential',
                max_length=20,
            ),
        ),
    ]
