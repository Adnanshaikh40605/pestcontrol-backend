from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0096_ecard_whatsapp_send'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PartnerAppVersionConfig',
        ),
    ]
