"""
Version 1 API URLs for the pest control application.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    health_check,
    ClientViewSet,
    InquiryViewSet,
    WebsiteLeadViewSet,
    JobCardViewSet,
    RenewalViewSet,
    DashboardViewSet,
    TechnicianViewSet,
    CRMInquiryViewSet,
    FeedbackViewSet,
    GlobalSearchView,
    CustomerHistoryView,
    ComplaintViewSet,
    StaffViewSet,
    ActivityLogViewSet,
    ReminderViewSet,
    CountryViewSet,
    StateViewSet,
    CityViewSet,
    LocationViewSet,
    QuotationViewSet,
)
from .remark_views import (
    CRMInquiryRemarkListCreateView,
    CRMInquiryRemarkDetailView,
    WebsiteLeadRemarkListCreateView,
    WebsiteLeadRemarkDetailView,
)
from .theme_views import UserThemeView
from .media_views import MediaFileView

# Create router for v1 API
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'website-leads', WebsiteLeadViewSet, basename='website-lead')
router.register(r'jobcards', JobCardViewSet, basename='jobcard')
router.register(r'renewals', RenewalViewSet, basename='renewal')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'technicians', TechnicianViewSet, basename='technician')
router.register(r'crm-inquiries', CRMInquiryViewSet, basename='crm-inquiry')
router.register(r'feedbacks', FeedbackViewSet, basename='feedback')
router.register(r'complaints', ComplaintViewSet, basename='complaint')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'activity-logs', ActivityLogViewSet, basename='activity-log')
router.register(r'reminders', ReminderViewSet, basename='reminder')
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'states', StateViewSet, basename='state')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'quotations', QuotationViewSet, basename='quotation')

urlpatterns = [
    path(
        'crm-inquiries/<int:inquiry_id>/remarks/',
        CRMInquiryRemarkListCreateView.as_view(),
        name='crm-inquiry-remarks',
    ),
    path(
        'crm-inquiries/remarks/<int:pk>/',
        CRMInquiryRemarkDetailView.as_view(),
        name='crm-inquiry-remark-detail',
    ),
    path(
        'website-leads/<int:lead_id>/remarks/',
        WebsiteLeadRemarkListCreateView.as_view(),
        name='website-lead-remarks',
    ),
    path(
        'website-leads/remarks/<int:pk>/',
        WebsiteLeadRemarkDetailView.as_view(),
        name='website-lead-remark-detail',
    ),
    path('users/theme/', UserThemeView.as_view(), name='user-theme'),
    path('media-file/', MediaFileView.as_view(), name='media-file'),
    path('health/', health_check, name='health_check'),
    path('global-search/', GlobalSearchView.as_view(), name='global_search'),
    path('customer-history/<int:client_id>/', CustomerHistoryView.as_view(), name='customer_history'),
    path('', include(router.urls)),
]
