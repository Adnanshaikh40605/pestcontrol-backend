# Generated manually to backfill client_address for existing job cards

from django.db import migrations
from django.db.models import Q


def backfill_client_address(apps, schema_editor):
    """
    Backfill client_address for existing job cards from their associated client's address.
    This ensures all job cards have an address, even those created before the client_address field was added.
    """
    JobCard = apps.get_model('core', 'JobCard')
    
    # Update all job cards that don't have a client_address (null or empty string) 
    # but their client has an address
    # We need to check both null and empty string cases
    jobcards_to_update = JobCard.objects.filter(
        Q(client_address__isnull=True) | Q(client_address='')
    ).exclude(
        Q(client__address__isnull=True) | Q(client__address='')
    ).select_related('client')
    
    updated_count = 0
    for jobcard in jobcards_to_update:
        if jobcard.client and jobcard.client.address and jobcard.client.address.strip():
            jobcard.client_address = jobcard.client.address
            jobcard.save(update_fields=['client_address'])
            updated_count += 1
    
    print(f"Backfilled client_address for {updated_count} job cards")


def reverse_backfill(apps, schema_editor):
    """
    Reverse migration - set client_address to null for job cards.
    This is not really necessary but included for completeness.
    """
    # In most cases, we don't want to reverse this migration
    # as it would remove valid data. So we'll do nothing here.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_alter_client_city'),
    ]

    operations = [
        migrations.RunPython(backfill_client_address, reverse_backfill),
    ]

