# Generated manually for Revenue Model v2 Phase 3 settlements

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('partner', '0008_revenue_model_v2_earnings'),
        ('core', '0094_revenue_model_v2'),
    ]

    operations = [
        migrations.CreateModel(
            name='TechnicianSettlement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('period_start', models.DateField(db_index=True)),
                ('period_end', models.DateField(db_index=True)),
                ('cadence', models.CharField(choices=[('weekly', 'Weekly'), ('monthly', 'Monthly')], db_index=True, default='weekly', max_length=20)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('pending_approval', 'Pending Approval'), ('approved', 'Approved'), ('paid', 'Paid'), ('cancelled', 'Cancelled')], db_index=True, default='draft', max_length=30)),
                ('gross_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[core.validators.validate_non_negative_decimal])),
                ('incentive_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[core.validators.validate_non_negative_decimal])),
                ('deduction_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[core.validators.validate_non_negative_decimal])),
                ('net_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[core.validators.validate_non_negative_decimal])),
                ('notes', models.TextField(blank=True, default='')),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_settlements', to=settings.AUTH_USER_MODEL)),
                ('paid_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paid_settlements', to=settings.AUTH_USER_MODEL)),
                ('partner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settlements', to='partner.partner', verbose_name='Partner')),
                ('technician', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlements', to='core.technician', verbose_name='Technician')),
            ],
            options={
                'verbose_name': 'Technician Settlement',
                'verbose_name_plural': 'Technician Settlements',
                'ordering': ['-period_end', '-id'],
            },
        ),
        migrations.CreateModel(
            name='SettlementLineItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('earning_type', models.CharField(choices=[('revenue_share', 'Revenue Share'), ('incentive', 'Incentive'), ('deduction', 'Deduction')], db_index=True, default='revenue_share', max_length=30)),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[core.validators.validate_non_negative_decimal])),
                ('notes', models.CharField(blank=True, default='', max_length=500)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlement_line_items', to='core.jobcard')),
                ('participation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settlement_line_items', to='core.jobcardtechnicianparticipation')),
                ('partner_earning', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settlement_line', to='partner.partnerearning')),
                ('settlement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='core.techniciansettlement')),
            ],
            options={
                'verbose_name': 'Settlement Line Item',
                'verbose_name_plural': 'Settlement Line Items',
                'ordering': ['id'],
            },
        ),
        migrations.AddIndex(
            model_name='techniciansettlement',
            index=models.Index(fields=['technician', 'status'], name='core_techni_technic_7a1c01_idx'),
        ),
        migrations.AddIndex(
            model_name='techniciansettlement',
            index=models.Index(fields=['period_start', 'period_end'], name='core_techni_period__b2c9d1_idx'),
        ),
        migrations.AddIndex(
            model_name='settlementlineitem',
            index=models.Index(fields=['settlement', 'earning_type'], name='core_settle_settlem_a1b2c3_idx'),
        ),
    ]
