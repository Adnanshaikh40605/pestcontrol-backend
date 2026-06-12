# Generated manually for payment collection feature

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import core.validators


def _parse_price(price_value):
    if price_value is None:
        return Decimal('0.00')
    raw = str(price_value).replace('₹', '').replace(',', '').strip()
    if not raw:
        return Decimal('0.00')
    try:
        return Decimal(raw).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def backfill_payment_amounts(apps, schema_editor):
    JobCard = apps.get_model('core', 'JobCard')

    for job in JobCard.objects.all().iterator():
        total = _parse_price(job.price)
        if total <= 0:
            continue

        job.total_amount = total
        if job.payment_status == 'Paid':
            job.paid_amount = total
            job.pending_amount = Decimal('0.00')
        elif job.status == 'Done' and job.payment_status == 'Unpaid':
            job.paid_amount = Decimal('0.00')
            job.pending_amount = total
            job.payment_status = 'Pending'
        else:
            job.paid_amount = Decimal('0.00')
            job.pending_amount = Decimal('0.00')

        job.save(update_fields=['total_amount', 'paid_amount', 'pending_amount', 'payment_status'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0080_backfill_reminders'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='paid_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Total amount collected so far',
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Paid Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='pending_amount',
            field=models.DecimalField(
                db_index=True,
                decimal_places=2,
                default=0,
                help_text='Outstanding balance remaining on this booking',
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Pending Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='total_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Total billable amount for this booking',
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Total Service Amount',
            ),
        ),
        migrations.AlterField(
            model_name='jobcard',
            name='payment_status',
            field=models.CharField(
                choices=[
                    ('Unpaid', 'Unpaid'),
                    ('Paid', 'Paid'),
                    ('Partially Paid', 'Partially Paid'),
                    ('Pending', 'Pending'),
                ],
                db_index=True,
                default='Unpaid',
                help_text='Current payment status of the job',
                max_length=20,
                verbose_name='Payment Status',
            ),
        ),
        migrations.CreateModel(
            name='BookingPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[core.validators.validate_positive_decimal])),
                ('payment_mode', models.CharField(choices=[('Cash', 'Cash'), ('Online', 'Online')], max_length=20)),
                ('collection_type', models.CharField(
                    choices=[
                        ('full', 'Full Payment'),
                        ('half', 'Half Payment'),
                        ('custom', 'Custom Pending'),
                        ('collection', 'Collection'),
                    ],
                    default='collection',
                    max_length=20,
                )),
                ('balance_after', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[core.validators.validate_non_negative_decimal])),
                ('remarks', models.TextField(blank=True, default='')),
                ('collected_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='booking_payments_collected',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('jobcard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_records', to='core.jobcard')),
            ],
            options={
                'verbose_name': 'Booking Payment',
                'verbose_name_plural': 'Booking Payments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='bookingpayment',
            index=models.Index(fields=['jobcard', '-created_at'], name='core_bookin_jobcard_6f0a2a_idx'),
        ),
        migrations.RunPython(backfill_payment_amounts, migrations.RunPython.noop),
    ]
