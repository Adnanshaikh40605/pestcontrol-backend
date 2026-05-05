import os
import django
import sys

# Add the current directory to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import JobCard
from rest_framework.test import APIRequestFactory
from core.views import JobCardViewSet
from django.utils import timezone
from django.contrib.auth.models import User

factory = APIRequestFactory()
view = JobCardViewSet()

# Mock user for permission check
user = User(is_staff=True, is_active=True, username='testadmin')

print("--- Testing Filter Logic (DRF) ---")

def test_tab(tab_id):
    request = factory.get('/api/v1/jobcards/', {'booking_type': tab_id})
    request.user = user
    # DRF View needs to wrap the request
    from rest_framework.request import Request
    drf_request = view.initialize_request(request)
    view.request = drf_request
    view.format_kwarg = None
    
    qs = view.get_queryset()
    print(f"Tab: {tab_id}, Count: {qs.count()}")
    for j in qs[:3]:
        print(f"  ID: {j.id}, Status: {j.status}")

test_tab('pending')
test_tab('done')
test_tab('all')
