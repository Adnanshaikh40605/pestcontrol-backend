# Generated manually for CRM Invoice + customer GSTIN snapshot.

from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0113_technician_settlement_set_null_on_delete'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('invoice_no', models.CharField(db_index=True, max_length=50, unique=True)),
                ('invoice_date', models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ('billed_by_name', models.CharField(blank=True, default='', max_length=255)),
                ('billed_by_address', models.TextField(blank=True, default='')),
                ('customer_name', models.CharField(db_index=True, max_length=255)),
                ('customer_mobile', models.CharField(blank=True, default='', max_length=20)),
                ('customer_address', models.TextField(blank=True, default='')),
                (
                    'customer_gst_number',
                    models.CharField(
                        blank=True,
                        default='',
                        help_text='Customer GSTIN captured at invoice time (e.g. 27AYTPA2835Q1ZR)',
                        max_length=30,
                    ),
                ),
                ('booking_code', models.CharField(blank=True, default='', max_length=50)),
                ('booking_created_at', models.DateField(blank=True, null=True)),
                ('next_service_date', models.DateField(blank=True, null=True)),
                ('reference', models.CharField(blank=True, default='', max_length=120)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('grand_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('notes', models.TextField(blank=True, default='')),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='created_invoices',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Invoice',
                'verbose_name_plural': 'Invoices',
                'ordering': ['-invoice_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('service', models.CharField(max_length=255)),
                ('schedule', models.CharField(blank=True, default='', max_length=100)),
                ('technician', models.CharField(blank=True, default='', max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                (
                    'invoice',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='items',
                        to='core.invoice',
                    ),
                ),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
