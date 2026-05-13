from django.urls import path
from . import apis

app_name = 'partner'

urlpatterns = [
    # ──────────────── AUTH ─────────────────
    path('register/', apis.RegisterAPIView.as_view(), name='register'),
    path('login/', apis.LoginAPIView.as_view(), name='login'),
    path('fcm-token/', apis.UpdateFCMTokenAPIView.as_view(), name='fcm-token'),

    # ──────────────── BOOKINGS ─────────────
    path('bookings/counts/', apis.BookingCountsAPIView.as_view(), name='booking-counts'),
    path('bookings/available/', apis.AvailableBookingsAPIView.as_view(), name='available-bookings'),
    path('bookings/accepted/', apis.AcceptedBookingsAPIView.as_view(), name='accepted-bookings'),
    path('bookings/completed/', apis.CompletedBookingsAPIView.as_view(), name='completed-bookings'),

    path('bookings/<int:id>/', apis.BookingDetailAPIView.as_view(), name='booking-detail'),
    path('bookings/<int:id>/accept/', apis.AcceptBookingAPIView.as_view(), name='accept-booking'),
    path('bookings/<int:id>/reject/', apis.RejectBookingAPIView.as_view(), name='reject-booking'),
    path('bookings/<int:id>/start/', apis.StartServiceAPIView.as_view(), name='start-service'),
    path('bookings/<int:id>/complete/', apis.CompleteBookingAPIView.as_view(), name='complete-booking'),

    # ──────────────── PROFILE ──────────────
    path('profile/', apis.ProfileAPIView.as_view(), name='profile'),
    path('earnings/', apis.EarningsHistoryAPIView.as_view(), name='earnings'),
    path('ratings/', apis.RatingsAPIView.as_view(), name='ratings'),
]
