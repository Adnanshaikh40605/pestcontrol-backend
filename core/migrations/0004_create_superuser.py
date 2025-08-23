from django.db import migrations
from django.contrib.auth.models import User


def create_superuser(apps, schema_editor):
    # Check if superuser already exists to avoid duplicates
    if not User.objects.filter(username="pest99").exists():
        User.objects.create_superuser(
            username="pest99",
            email="pest99@example.com",
            password="pest991122"
        )


def reverse_create_superuser(apps, schema_editor):
    # Remove the superuser if migration is reversed
    User = apps.get_model('auth', 'User')
    User.objects.filter(username="pest99").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_inquiry_is_read_and_more'),
    ]

    operations = [
        migrations.RunPython(create_superuser, reverse_create_superuser),
    ]
