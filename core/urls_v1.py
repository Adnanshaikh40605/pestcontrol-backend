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
from .notification_views import (
    DeviceTokenViewSet,
    NotificationLogViewSet,
    NotificationViewSet,
    firebase_health_check,
)

# Create router for v1 API
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'jobcards', JobCardViewSet, basename='jobcard')
router.register(r'renewals', RenewalViewSet, basename='renewal')

# Simplified notification endpoints
router.register(r'device-tokens', DeviceTokenViewSet, basename='device-token')
router.register(r'notification-logs', NotificationLogViewSet, basename='notification-log')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('firebase/health/', firebase_health_check, name='firebase_health_check'),
    path('', include(router.urls)),
]
