
from django.db import migrations

def populate_normalized_name(apps, schema_editor):
    Location = apps.get_model('core', 'Location')
    for loc in Location.objects.all():
        if loc.name:
            loc.normalized_name = "".join(loc.name.lower().split())
            loc.save()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_alter_location_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_normalized_name),
    ]
