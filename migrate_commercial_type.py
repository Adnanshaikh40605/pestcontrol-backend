import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import JobCard

def migrate():
    print("Starting migration of commercial_type...")
    
    # 1. Migrate Society bookings
    society_count = JobCard.objects.filter(job_type='Society').update(
        commercial_type='society',
        is_price_estimated=True
    )
    print(f"Updated {society_count} society bookings.")
    
    # 2. Migrate Customer bookings
    customer_count = JobCard.objects.filter(job_type='Customer').update(
        commercial_type='home',
        is_price_estimated=False
    )
    print(f"Updated {customer_count} customer bookings.")
    
    # 3. Handle any remaining (fallback)
    remaining_count = JobCard.objects.filter(commercial_type='').update(
        commercial_type='home'
    )
    if remaining_count:
        print(f"Updated {remaining_count} remaining bookings to 'home'.")

    print("Migration complete!")

if __name__ == "__main__":
    migrate()
