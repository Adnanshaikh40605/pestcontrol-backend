from django.urls import path

from . import apis

app_name = 'staff_tracking'

urlpatterns = [
    # Auth (mobile)
    path('auth/login/', apis.LoginAPIView.as_view(), name='login'),
    path('auth/refresh/', apis.RefreshTokenAPIView.as_view(), name='refresh'),

    # Mobile — staff self-service
    path('me/', apis.MeAPIView.as_view(), name='me'),
    path('me/attendance/', apis.MyAttendanceAPIView.as_view(), name='my-attendance'),
    path('consent/', apis.ConsentAPIView.as_view(), name='consent'),
    path('attendance/checkin/', apis.CheckInAPIView.as_view(), name='checkin'),
    path('attendance/checkout/', apis.CheckOutAPIView.as_view(), name='checkout'),
    path('location/ping/', apis.LocationPingAPIView.as_view(), name='location-ping'),
    path('location/batch/', apis.LocationBatchAPIView.as_view(), name='location-batch'),

    # CRM dashboard
    path('live/', apis.LiveStaffAPIView.as_view(), name='live'),
    path('staff/', apis.StaffDirectoryAPIView.as_view(), name='staff-directory'),
    path('attendance/today/', apis.AttendanceTodayAPIView.as_view(), name='attendance-today'),
    path('attendance/report/', apis.AttendanceReportAPIView.as_view(), name='attendance-report'),
    path('location/history/<int:technician_id>/', apis.LocationHistoryAPIView.as_view(), name='location-history'),
    path('location/distance/', apis.DistanceReportAPIView.as_view(), name='distance-report'),
    path('settings/', apis.SettingsAPIView.as_view(), name='settings'),
]
