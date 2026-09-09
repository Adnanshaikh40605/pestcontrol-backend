"""Third technician type: 'secondary'.

A secondary technician is paid exactly like a partner (40/60 pool share and
settlements) but never receives the partner-app booking broadcast — desk staff
assign each job to them by hand.

Hand-written because `makemigrations` cannot serialize the lru_cache-wrapped
storage callable on an unrelated core FileField. Choices are inlined here (as
in 0094, which first added this field), so extending the enum needs the full
list repeated.
"""

from django.db import migrations, models


TECHNICIAN_TYPE_CHOICES = [
    ('partner', 'Partner'),
    ('salaried', 'Salaried'),
    ('secondary', 'Secondary (Manual Assign)'),
]

TECHNICIAN_TYPE_HELP = (
    'Partner (40/60 share, sees app broadcast), salaried (salary only), '
    'or secondary (40/60 share but no broadcast — staff assign manually)'
)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0108_pricing_rate_floor_and_segments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='technician',
            name='technician_type',
            field=models.CharField(
                choices=TECHNICIAN_TYPE_CHOICES,
                db_index=True,
                default='partner',
                help_text=TECHNICIAN_TYPE_HELP,
                max_length=20,
                verbose_name='Technician Type',
            ),
        ),
    ]
