# Generated manually for Revenue Model v2 (additive, conflict-safe)

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models

import core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0007_partner_referral'),
        ('core', '0093_booking_report_client_mobile_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='technician',
            name='technician_type',
            field=models.CharField(
                choices=[('partner', 'Partner'), ('salaried', 'Salaried')],
                db_index=True,
                default='partner',
                help_text='Partner (40/60 share) or salaried (salary only)',
                max_length=20,
                verbose_name='Technician Type',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='branch',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='technician',
            name='aadhaar',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='technician',
            name='pan',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='technician',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='technician_photos/%Y/%m/', verbose_name='Photo'),
        ),
        migrations.AddField(
            model_name='technician',
            name='agreement_file',
            field=models.FileField(blank=True, null=True, upload_to='technician_agreements/%Y/%m/', verbose_name='Agreement File'),
        ),
        migrations.AddField(
            model_name='technician',
            name='security_deposit_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Security Deposit Amount',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='security_deposit_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('collected', 'Collected'), ('refunded', 'Refunded')],
                default='pending',
                max_length=20,
                verbose_name='Security Deposit Status',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='skills',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='technician',
            name='star_rating',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=3,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Star Rating',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='presence_status',
            field=models.CharField(
                choices=[
                    ('online', 'Online'),
                    ('offline', 'Offline'),
                    ('busy', 'Busy'),
                    ('on_service', 'On Service'),
                    ('on_leave', 'On Leave'),
                    ('suspended', 'Suspended'),
                ],
                db_index=True,
                default='offline',
                max_length=20,
                verbose_name='Presence Status',
            ),
        ),
        migrations.AddField(
            model_name='technician',
            name='suspended_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='technician',
            name='suspend_reason',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='technician',
            name='reactivated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='package_tier',
            field=models.CharField(
                blank=True,
                choices=[('standard', 'Standard'), ('premium', 'Premium')],
                db_index=True,
                default='',
                max_length=20,
                verbose_name='Package Tier',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='payment_model',
            field=models.CharField(
                blank=True,
                choices=[('revenue_sharing', 'Revenue Sharing'), ('salaried', 'Salaried')],
                db_index=True,
                default='',
                help_text='revenue_sharing (40/60) or salaried; blank for legacy',
                max_length=30,
                verbose_name='Payment Model',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='technician_share_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('40.00'),
                max_digits=5,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Technician Share %',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='company_share_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('60.00'),
                max_digits=5,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Company Share %',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='planned_visit_count',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Contractual/AMC divisor; falls back to max_cycle when null',
                null=True,
                verbose_name='Planned Visit Count',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='discount_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Discount Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='visit_revenue_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Visit Revenue Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='technician_pool_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Technician Pool Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='company_share_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Company Share Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='visit_payout_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Lead / primary partner snapshot; crew rows have their own snapshots',
                max_digits=12,
                validators=[core.validators.validate_non_negative_decimal],
                verbose_name='Visit Payout Amount',
            ),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='payout_status',
            field=models.CharField(
                choices=[
                    ('legacy_exempt', 'Legacy Exempt'),
                    ('not_applicable', 'Not Applicable'),
                    ('pending', 'Pending'),
                    ('held', 'Held'),
                    ('approved', 'Approved'),
                    ('paid', 'Paid'),
                    ('cancelled', 'Cancelled'),
                ],
                db_index=True,
                default='legacy_exempt',
                max_length=20,
                verbose_name='Payout Status',
            ),
        ),
        migrations.CreateModel(
            name='JobCardTechnicianParticipation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('role', models.CharField(choices=[('lead', 'Lead'), ('crew', 'Crew')], db_index=True, default='crew', max_length=20)),
                ('attendance_status', models.CharField(choices=[('assigned', 'Assigned'), ('checked_in', 'Checked In'), ('completed', 'Completed'), ('absent', 'Absent')], db_index=True, default='assigned', max_length=20)),
                ('checked_in_at', models.DateTimeField(blank=True, null=True)),
                ('checked_out_at', models.DateTimeField(blank=True, null=True)),
                ('is_payout_eligible', models.BooleanField(default=True, help_text='False for salaried techs (salary only; excluded from 40% divisor)')),
                ('share_percent_snapshot', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('payout_amount_snapshot', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[core.validators.validate_non_negative_decimal])),
                ('jobcard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='technician_participations', to='core.jobcard', verbose_name='Job Card')),
                ('partner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_participations', to='partner.partner', verbose_name='Partner')),
                ('technician', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_participations', to='core.technician', verbose_name='Technician')),
            ],
            options={
                'verbose_name': 'Job Card Technician Participation',
                'verbose_name_plural': 'Job Card Technician Participations',
                'ordering': ['role', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='jobcardtechnicianparticipation',
            index=models.Index(fields=['jobcard', 'attendance_status'], name='core_jobcar_jobcard_fef032_idx'),
        ),
        migrations.AddIndex(
            model_name='jobcardtechnicianparticipation',
            index=models.Index(fields=['jobcard', 'is_payout_eligible'], name='core_jobcar_jobcard_e813ce_idx'),
        ),
        migrations.AddConstraint(
            model_name='jobcardtechnicianparticipation',
            constraint=models.UniqueConstraint(fields=('jobcard', 'technician'), name='unique_jobcard_technician_participation'),
        ),
        # Existing rows keep default payout_status=legacy_exempt (AddField default).
        # Linked partner techs stay technician_type=partner (AddField default).
    ]
