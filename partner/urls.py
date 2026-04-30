from django.urls import path
from . import apis

urlpatterns = [
    path('login/', apis.login),
    path('available/', apis.available_bookings),
    path('accepted/', apis.accepted_bookings),
    path('accept/<int:pk>/', apis.accept_booking),
    path('complete/<int:pk>/', apis.complete_booking),
]
