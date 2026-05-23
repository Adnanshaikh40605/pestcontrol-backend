from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0004_partner_push_notifications'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='partner',
            name='fcm_token',
        ),
        migrations.DeleteModel(
            name='PartnerDeviceToken',
        ),
    ]
