from django.urls import path

from . import apis

app_name = 'customer'

urlpatterns = [
    path('register/', apis.RegisterAPIView.as_view(), name='register'),
    path('login/', apis.LoginAPIView.as_view(), name='login'),
    path('token/refresh/', apis.RefreshTokenAPIView.as_view(), name='token-refresh'),
    path('profile/', apis.ProfileAPIView.as_view(), name='profile'),
    path('catalog/', apis.CatalogAPIView.as_view(), name='catalog'),
    path('bookings/', apis.BookingListCreateAPIView.as_view(), name='bookings'),
    path('bookings/<int:id>/', apis.BookingDetailAPIView.as_view(), name='booking-detail'),
    path('bookings/<int:id>/pay/', apis.ConfirmPaymentAPIView.as_view(), name='booking-pay'),
    path('bookings/<int:id>/rate/', apis.RateBookingAPIView.as_view(), name='booking-rate'),
    path('bookings/<int:id>/invoice/', apis.InvoiceAPIView.as_view(), name='booking-invoice'),
    path('history/', apis.ServiceHistoryAPIView.as_view(), name='history'),
    path('amc-schedule/', apis.AMCScheduleAPIView.as_view(), name='amc-schedule'),
]
