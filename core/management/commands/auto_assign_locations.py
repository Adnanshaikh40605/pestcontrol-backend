from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import JobCard, Location, City, State, Country

class Command(BaseCommand):
    help = 'Auto-assign master locations to existing JobCards based on address keywords'

    def handle(self, *args, **options):
        self.stdout.write('Starting auto-assignment of locations...')

        # Ensure default master records exist
        india = Country.objects.get(name='India')
        maharashtra = State.objects.get(name='Maharashtra', country=india)
        
        # Get all active locations for matching
        all_locations = Location.objects.filter(is_active=True).select_related('city')
        
        # Build a search map
        location_map = {}
        for loc in all_locations:
            location_map[loc.name.lower()] = loc

        # Manual mappings for common variations or typos
        manual_mappings = {
            'mira byader': 'Mira Road',
            'mira bhayander': 'Mira Road',
            'dadr': 'Dadar',
            'mahim': 'Mahim East',
        }

        # Get JobCards that need location assignment
        jobs_to_update = JobCard.objects.filter(master_location__isnull=True)
        
        total_scanned = jobs_to_update.count()
        matched_count = 0
        unmatched_count = 0

        self.stdout.write(f'Scanning {total_scanned} records...')

        for job in jobs_to_update:
            address_text = (job.client_address or "").lower()
            legacy_city = (job.city or "").lower()
            combined_text = f"{address_text} {legacy_city}"
            
            matched_loc = None
            
            # 1. Check manual mappings first
            for typo, loc_name in manual_mappings.items():
                if typo in combined_text:
                    matched_loc = Location.objects.filter(name__iexact=loc_name).first()
                    if matched_loc: break

            # 2. Keyword matching
            if not matched_loc:
                sorted_keywords = sorted(location_map.keys(), key=len, reverse=True)
                for keyword in sorted_keywords:
                    if keyword in combined_text:
                        matched_loc = location_map[keyword]
                        break
            
            if matched_loc:
                job.master_location = matched_loc
                job.master_city = matched_loc.city
                job.master_state = maharashtra
                job.master_country = india
                
                # Update full_address if empty
                if not job.full_address:
                    job.full_address = job.client_address
                
                job.save()
                matched_count += 1
                if matched_count % 50 == 0:
                    self.stdout.write(f'  - Processed {matched_count} matches...')
            else:
                unmatched_count += 1

        self.stdout.write('\n' + '='*30)
        self.stdout.write(self.style.SUCCESS(f'Total bookings scanned: {total_scanned}'))
        self.stdout.write(self.style.SUCCESS(f'Matched successfully: {matched_count}'))
        self.stdout.write(self.style.WARNING(f'Not matched: {unmatched_count}'))
        self.stdout.write('='*30)
        
        if unmatched_count > 0:
            self.stdout.write(self.style.NOTICE('Unmatched records remain for manual correction.'))
