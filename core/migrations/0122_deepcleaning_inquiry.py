# Generated manually for DeepCleaning99 inquiries (isolated from pest Website Leads).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0121_gst_invoice_and_purchase_bills'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeepCleaningInquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('mobile', models.CharField(db_index=True, max_length=10, validators=[core.validators.validate_mobile_number])),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('city', models.CharField(db_index=True, default='Mumbai', max_length=100)),
                ('area', models.CharField(blank=True, default='', max_length=150)),
                ('address', models.TextField(blank=True, default='')),
                ('segment', models.CharField(blank=True, default='Residential', help_text='Residential or Commercial', max_length=50)),
                ('service', models.CharField(db_index=True, max_length=255)),
                ('package_name', models.CharField(blank=True, default='', max_length=255)),
                ('package_id', models.CharField(blank=True, default='', max_length=50)),
                ('quantity', models.CharField(blank=True, default='', max_length=50)),
                ('unit', models.CharField(blank=True, default='', max_length=50)),
                ('plan', models.CharField(blank=True, default='one', help_text='one / amc', max_length=50)),
                ('property_size', models.CharField(blank=True, default='', max_length=50)),
                ('property_type', models.CharField(blank=True, default='', max_length=50)),
                ('preferred_date', models.DateField(blank=True, db_index=True, null=True)),
                ('preferred_time', models.CharField(blank=True, default='', max_length=100)),
                ('estimated_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[core.validators.validate_non_negative_decimal])),
                ('regular_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[core.validators.validate_non_negative_decimal])),
                ('discount_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[core.validators.validate_non_negative_decimal])),
                ('notes', models.TextField(blank=True, default='')),
                ('page_url', models.URLField(blank=True, max_length=500, null=True)),
                ('source', models.CharField(blank=True, db_index=True, default='deepcleaning99', max_length=50)),
                ('status', models.CharField(choices=[('New', 'New'), ('Contacted', 'Contacted'), ('Converted', 'Converted'), ('Closed', 'Closed')], db_index=True, default='New', max_length=20)),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_deepcleaning_inquiries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'DeepCleaning99 Inquiry',
                'verbose_name_plural': 'DeepCleaning99 Inquiries',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='DeepCleaningInquiryRemark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('remark', models.TextField()),
                ('remark_type', models.CharField(choices=[('CALL', 'Call'), ('FOLLOWUP', 'Follow-up'), ('NOTE', 'Note'), ('CONVERT', 'Convert'), ('SYSTEM', 'System')], db_index=True, default='NOTE', max_length=20)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deepcleaning_inquiry_remarks', to=settings.AUTH_USER_MODEL)),
                ('inquiry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remarks', to='core.deepcleaninginquiry')),
            ],
            options={
                'verbose_name': 'DeepCleaning99 Inquiry Remark',
                'verbose_name_plural': 'DeepCleaning99 Inquiry Remarks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='deepcleaninginquiry',
            index=models.Index(fields=['status', '-created_at'], name='core_deepcl_status_a5fc04_idx'),
        ),
        migrations.AddIndex(
            model_name='deepcleaninginquiry',
            index=models.Index(fields=['is_read', '-created_at'], name='core_deepcl_is_read_b2f906_idx'),
        ),
        migrations.AddIndex(
            model_name='deepcleaninginquiry',
            index=models.Index(fields=['mobile', '-created_at'], name='core_deepcl_mobile_49bd22_idx'),
        ),
        migrations.AddIndex(
            model_name='deepcleaninginquiryremark',
            index=models.Index(fields=['inquiry', '-created_at'], name='core_deepcl_inquiry_e78ced_idx'),
        ),
    ]
