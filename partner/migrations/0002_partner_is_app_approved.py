from django.db import migrations, models


def approve_existing_partners(apps, schema_editor):
    Partner = apps.get_model('partner', 'Partner')
    Partner.objects.filter(core_technician_id__isnull=False, is_active=True).update(is_app_approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='is_app_approved',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='CRM admin must approve before technician can use the mobile app',
                verbose_name='Partner App Approved',
            ),
        ),
        migrations.RunPython(approve_existing_partners, migrations.RunPython.noop),
    ]
