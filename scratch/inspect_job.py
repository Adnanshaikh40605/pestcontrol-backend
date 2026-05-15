from core.models import JobCard
import django
import os
import sys

# Setup django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

j = JobCard.objects.filter(status='Done').order_by('-updated_at').first()
if j:
    print(f'ID: {j.id}')
    print(f'Code: {j.code}')
    print(f'Price Raw: "{j.price}"')
    print(f'Booking Type: {j.booking_type}')
    print(f'Completed At: {j.completed_at}')
    print(f'Updated At: {j.updated_at}')
else:
    print('No Done jobs found')
