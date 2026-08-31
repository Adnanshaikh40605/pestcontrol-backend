# Generated manually — remove CRM/backend app version force-update tables.
# Apps now use Google Play in-app updates instead.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0101_technician_service_cities'),
    ]

    operations = [
        migrations.DeleteModel(name='CustomerAppVersionConfig'),
        migrations.DeleteModel(name='PartnerAppVersionConfig'),
    ]
