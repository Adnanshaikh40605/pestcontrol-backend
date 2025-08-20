"""
Version 1 API URLs for the pest control application.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    health_check,
    ClientViewSet,
    InquiryViewSet,
    JobCardViewSet,
    RenewalViewSet,
)

# Create router for v1 API
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'jobcards', JobCardViewSet, basename='jobcard')
router.register(r'renewals', RenewalViewSet, basename='renewal')

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('', include(router.urls)),
]
