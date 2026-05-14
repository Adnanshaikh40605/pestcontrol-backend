from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Location, JobCard, ActivityLog
from django.db.models import Count

class Command(BaseCommand):
    help = 'Clean up duplicate locations by normalizing names and merging records.'

    def handle(self, *args, **options):
        self.stdout.write('Starting location cleanup...')

        with transaction.atomic():
            # 1. Normalize all existing names first
            locations = Location.objects.all()
            for loc in locations:
                normalized = Location.normalize_text(loc.name)
                if loc.normalized_name != normalized:
                    loc.normalized_name = normalized
                    loc.save(update_fields=['normalized_name'])

            # 2. Find duplicates (same city, same normalized name)
            duplicates = (
                Location.objects.values('city', 'normalized_name')
                .annotate(count=Count('id'))
                .filter(count__gt=1)
            )

            total_merged = 0
            for dup in duplicates:
                city_id = dup['city']
                normalized_name = dup['normalized_name']
                
                # Get all records for this duplicate group, ordered by created_at (keep oldest)
                records = list(Location.objects.filter(
                    city_id=city_id, 
                    normalized_name=normalized_name
                ).order_by('created_at'))
                
                original = records[0]
                others = records[1:]
                
                for duplicate in others:
                    # Update JobCard references
                    affected_jobs = JobCard.objects.filter(master_location=duplicate).update(master_location=original)
                    
                    self.stdout.write(f"Merged '{duplicate.name}' into '{original.name}' ({affected_jobs} jobs updated)")
                    
                    # Log the merge
                    ActivityLog.objects.create(
                        action="Location Merged",
                        details=f"Merged duplicate location '{duplicate.name}' (ID: {duplicate.id}) into '{original.name}' (ID: {original.id}). {affected_jobs} jobs updated."
                    )
                    
                    duplicate.delete()
                    total_merged += 1

            self.stdout.write(self.style.SUCCESS(f'Successfully merged {total_merged} duplicate locations.'))
