"""
Main URL configuration for core app with API versioning.
"""
from django.urls import path, include

urlpatterns = [
    # API v1 endpoints
    path('v1/', include('core.urls_v1')),
    
    # Default to v1 for backward compatibility
    path('', include('core.urls_v1')),
]


