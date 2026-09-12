# Seller/company GSTIN snapshot on Invoice (optional; empty omits from PDF).

from django.db import migrations, models


DEFAULT_COMPANY_GSTIN = '27ACEFM4002G1ZM'


def backfill_billed_by_gst(apps, schema_editor):
    Invoice = apps.get_model('core', 'Invoice')
    Invoice.objects.filter(billed_by_gst_number='').update(
        billed_by_gst_number=DEFAULT_COMPANY_GSTIN,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0115_jobcard_gst_paid_extra_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='billed_by_gst_number',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Seller/company GSTIN snapshot at invoice time (empty = omit from PDF)',
                max_length=30,
            ),
        ),
        migrations.RunPython(backfill_billed_by_gst, noop_reverse),
    ]
