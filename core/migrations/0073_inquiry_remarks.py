# Generated manually for remark history upgrade

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_remarks(apps, schema_editor):
    CRMInquiry = apps.get_model('core', 'CRMInquiry')
    Inquiry = apps.get_model('core', 'Inquiry')
    InquiryRemark = apps.get_model('core', 'InquiryRemark')
    WebsiteLeadRemark = apps.get_model('core', 'WebsiteLeadRemark')

    for inquiry in CRMInquiry.objects.exclude(remark__isnull=True).exclude(remark=''):
        if InquiryRemark.objects.filter(inquiry_id=inquiry.id).exists():
            continue
        InquiryRemark.objects.create(
            inquiry_id=inquiry.id,
            remark=inquiry.remark,
            created_by_id=inquiry.created_by_id,
            remark_type='NOTE',
        )

    for lead in Inquiry.objects.exclude(remark__isnull=True).exclude(remark=''):
        if WebsiteLeadRemark.objects.filter(lead_id=lead.id).exists():
            continue
        WebsiteLeadRemark.objects.create(
            lead_id=lead.id,
            remark=lead.remark,
            created_by_id=lead.created_by_id,
            remark_type='NOTE',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0072_userprofile_technician_role'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InquiryRemark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('remark', models.TextField()),
                ('remark_type', models.CharField(choices=[('CALL', 'Call'), ('FOLLOWUP', 'Follow-up'), ('NOTE', 'Note'), ('CONVERT', 'Convert'), ('SYSTEM', 'System')], db_index=True, default='NOTE', max_length=20)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crm_inquiry_remarks', to=settings.AUTH_USER_MODEL)),
                ('inquiry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remarks', to='core.crminquiry')),
            ],
            options={
                'verbose_name': 'CRM Inquiry Remark',
                'verbose_name_plural': 'CRM Inquiry Remarks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WebsiteLeadRemark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('remark', models.TextField()),
                ('remark_type', models.CharField(choices=[('CALL', 'Call'), ('FOLLOWUP', 'Follow-up'), ('NOTE', 'Note'), ('CONVERT', 'Convert'), ('SYSTEM', 'System')], db_index=True, default='NOTE', max_length=20)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='website_lead_remarks', to=settings.AUTH_USER_MODEL)),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remarks', to='core.inquiry')),
            ],
            options={
                'verbose_name': 'Website Lead Remark',
                'verbose_name_plural': 'Website Lead Remarks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='inquiryremark',
            index=models.Index(fields=['inquiry', '-created_at'], name='core_inquir_inquiry_6e8f2a_idx'),
        ),
        migrations.AddIndex(
            model_name='websiteleadremark',
            index=models.Index(fields=['lead', '-created_at'], name='core_websit_lead_id_2c4b91_idx'),
        ),
        migrations.RunPython(migrate_legacy_remarks, migrations.RunPython.noop),
    ]
