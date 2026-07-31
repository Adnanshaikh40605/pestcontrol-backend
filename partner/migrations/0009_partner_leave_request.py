# Generated manually — Partner leave requests (revenue model Phase 4)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0008_revenue_model_v2_earnings'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerLeaveRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(db_index=True)),
                ('end_date', models.DateField(db_index=True)),
                ('reason', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], db_index=True, default='pending', max_length=20)),
                ('admin_note', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('partner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_requests', to='partner.partner')),
            ],
            options={
                'verbose_name': 'Partner Leave Request',
                'verbose_name_plural': 'Partner Leave Requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='partnerleaverequest',
            index=models.Index(fields=['partner', 'status'], name='partner_par_partner_leave_idx'),
        ),
    ]
