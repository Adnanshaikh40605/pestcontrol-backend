from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0120_jobcard_gst_pricing_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='supply_category',
            field=models.CharField(
                blank=True,
                choices=[('B2B', 'B2B'), ('B2C', 'B2C')],
                default='',
                help_text='Blank keeps older invoices on the previous tax field.',
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='customer_state',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='invoice',
            name='place_of_supply',
            field=models.CharField(blank=True, default='Maharashtra', max_length=80),
        ),
        migrations.AddField(
            model_name='invoice',
            name='sac_code',
            field=models.CharField(blank=True, default='998531', max_length=12),
        ),
        migrations.AddField(
            model_name='invoice',
            name='gst_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('18.00'), max_digits=5),
        ),
        migrations.AddField(
            model_name='invoice',
            name='cgst_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='invoice',
            name='sgst_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='invoice',
            name='igst_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='invoice',
            name='payment_received',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='invoice',
            name='customer_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='invoice',
            name='payment_terms',
            field=models.CharField(blank=True, default='Due end of next month', max_length=120),
        ),
        migrations.AddField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='is_cancelled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='invoice',
            name='note_kind',
            field=models.CharField(
                blank=True,
                choices=[('', 'Invoice'), ('credit', 'Credit note'), ('debit', 'Debit note')],
                default='',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='bank_ifsc',
            field=models.CharField(blank=True, default='IDFB0040115', max_length=20),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='quantity',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=10),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='sac_code',
            field=models.CharField(blank=True, default='', max_length=12),
        ),
        migrations.CreateModel(
            name='PurchaseBill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('supplier_name', models.CharField(max_length=255)),
                ('supplier_gstin', models.CharField(blank=True, default='', max_length=30)),
                ('bill_number', models.CharField(max_length=80)),
                ('bill_date', models.DateField(db_index=True)),
                ('taxable_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('cgst_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('sgst_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('igst_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('attachment', models.FileField(blank=True, upload_to='purchase_bills/%Y/%m/')),
                ('input_eligibility', models.CharField(
                    choices=[
                        ('pending', 'Pending CA review'),
                        ('eligible', 'Eligible input'),
                        ('not_eligible', 'Not eligible'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('notes', models.TextField(blank=True, default='')),
            ],
            options={'ordering': ['-bill_date', '-id']},
        ),
        migrations.AddConstraint(
            model_name='purchasebill',
            constraint=models.UniqueConstraint(
                fields=('supplier_gstin', 'bill_number'),
                name='unique_supplier_bill_number',
            ),
        ),
        migrations.CreateModel(
            name='GstCaSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ca_email', models.EmailField(blank=True, default='', max_length=254)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'GST CA settings'},
        ),
        migrations.CreateModel(
            name='CaReportDispatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('ca_email', models.EmailField(max_length=254)),
                ('status', models.CharField(max_length=20)),
                ('detail', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
