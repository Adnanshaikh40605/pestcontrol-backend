from django.core.management.base import BaseCommand
from core.models import Country, State, City, Location

class Command(BaseCommand):
    help = 'Setup master locations (Country, State, Cities, and Locations)'

    def handle(self, *args, **options):
        self.stdout.write('Setting up master locations...')

        # 1. Setup Country
        country, created = Country.objects.get_or_create(name='India')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Country: {country.name}'))

        # 2. Setup State
        state, created = State.objects.get_or_create(country=country, name='Maharashtra')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created State: {state.name}'))

        # 3. Setup Cities and Locations
        data = {
            'Mumbai': [
                'Mankhurd', 'Bandra West', 'Marine Lines', 'Jogeshwari East', 'Jogeshwari West', 
                'Malad East', 'Malad West', 'Mahim East', 'Mahim West', 'Sion West', 'Thane West', 
                'Matunga West', 'Dadar East', 'Dadar West', 'Goregaon East', 'Goregaon West', 
                'Kurla West', 'Ghatkopar West', 'Borivali East', 'Borivali West', 'Vile Parle East', 
                'Colaba', 'Fort', 'Mira Road West', 'Khar West', 'Santacruz East', 'Nalasopara', 
                'Mira Road', 'Andheri West', 'Bhayander West', 'Dahisar East', 'Khar East', 
                'Santacruz West', 'Kandivali East', 'Kandivali West', 'Dahisar West', 'Bhayander East', 
                'Vile Parle West', 'Sewree', 'Vasai', 'Kelwa', 'Govandi', 'Andheri East', 
                'Currey Road', 'Nepean Sea Road', 'Ghatkopar East', 'Sandhurst Road', 'Kanjurmarg East', 
                'Mulund', 'Wadala', 'Kurla', 'Kalyan East', 'Vikhroli', 'Byculla', 'Worli', 'Sion', 
                'Masjid Bunder', 'Mahalaxmi', 'Lower Parel', 'Mumbai Central', 'Vikhroli East', 
                'Ghatkopar', 'Prabhadevi', 'Chinchpokli', 'Govandi West', 'Churchgate', 'Bandra East', 
                'Chunabhatti', 'Grant Road', 'Breach Candy', 'Powai', 'Virar', 'Chembur West', 
                'Dharavi', 'Vidya Vihar', 'Dadar', 'Bhandup East', 'Parel', 'Altamount Road', 
                'Tardeo', 'Mazgaon', 'Dockyard Road', 'Reay Road', 'Girgaon', 'Charni Road', 
                'Nariman Point', 'Wadi Bandar', 'Cuffe Parade', 'Peddar Road', 'Kalachowki', 
                'Cotton Green', 'Walkeshwar', 'kanjurmarg'
            ],
            'Pune': [
                'Shivaji Nagar', 'Akurdi', 'Swargate', 'Hadapsar', 'Katraj', 'Yerwada', 'Nigdi', 
                'Sangamwadi', 'Viman Nagar', 'Belewadi', 'Bhosari', 'Baner', 'Kondhwa', 'Mohammadwadi', 
                'Keshav Nagar', 'Mundwa', 'Rasta Peth', 'Somwar Peth', 'Pimpri Saudagar', 'Pimpri Nilakh', 
                'Camp', 'Uruli', 'Nanded City', 'Market Yard', 'Talegaon', 'Vishrant Vadi', 'Manjari', 
                'Wakad', 'Ghorpadi', 'Wagholi', 'Narhe', 'Wanowrie', 'Bibewadi', 'Warje', 'Wadgaon Sheri', 
                'Hinjewadi', 'Kothrud', 'Moshi', 'Dighi', 'Kharadi', 'Aundh', 'Kalyani Nagar', 'Bhugaon', 
                'Rahatani', 'Parvati', 'Pashan', 'Navi Peth', 'Balewadi', 'Shukravar Peth', 'Dhankawadi', 
                'Wadki', 'Dhanori', 'Dhayari', 'Khadki', 'Deccan', 'Fursungi', 'Shaniwar Wada', 
                'Charholi Budruk', 'Phulgaon', 'Morewadi', 'Pimpri-Chinchwad', 'Bavdhan', 'Koregaon Park', 
                'Fatima Nagar', 'Lohegaon', 'Undri', 'Dehu Road', 'Bopodi', 'Vadgaon'
            ],
            'Navi Mumbai': [
                'Rabale', 'Airoli', 'Belapur', 'Kamothe', 'Kharghar', 'Ulwe', 'Turbhe', 'Nerul', 
                'Panvel', 'Ghansoli', 'Kalamboli', 'Seawood', 'Sanpada', 'Vashi', 'Taloja', 
                'KoparKhairane', 'khandeshwar'
            ],
            'Thane': [
                'Ambernath', 'Titwala', 'Bhiwandi', 'Dombivali East', 'Diva East', 'Ulhasnagar', 
                'Thane', 'Karjat', 'Mumbra', 'Kalwa West', 'Diva West', 'Thakurli', 'Dombivali West', 
                'Kalyan', 'Dombivali', 'Shahad', 'Badlapur West', 'Badlapur East', 'padgha', 'Khopoli'
            ]
        }

        for city_name, locations in data.items():
            city, created = City.objects.get_or_create(state=state, name=city_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created City: {city_name}'))
            
            for loc_name in locations:
                loc, created = Location.objects.get_or_create(city=city, name=loc_name.strip())
                if created:
                    self.stdout.write(f'  - Created Location: {loc_name}')

        self.stdout.write(self.style.SUCCESS('Successfully setup master locations!'))
