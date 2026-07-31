# Generated manually for Revenue Model v2 PartnerEarning extensions

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0094_revenue_model_v2'),
        ('partner', '0007_partner_referral'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerearning',
            name='earning_type',
            field=models.CharField(
                choices=[
                    ('revenue_share', 'Revenue Share'),
                    ('incentive', 'Incentive'),
                    ('deduction', 'Deduction'),
                ],
                db_index=True,
                default='revenue_share',
                max_length=30,
                verbose_name='Earning Type',
            ),
        ),
        migrations.AddField(
            model_name='partnerearning',
            name='is_approved',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Is Approved'),
        ),
        migrations.AddField(
            model_name='partnerearning',
            name='participation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='partner_earnings',
                to='core.jobcardtechnicianparticipation',
                verbose_name='Participation',
            ),
        ),
        migrations.AddConstraint(
            model_name='partnerearning',
            constraint=models.UniqueConstraint(
                fields=('job', 'partner', 'earning_type'),
                name='unique_partner_earning_per_job_type',
            ),
        ),
    ]
