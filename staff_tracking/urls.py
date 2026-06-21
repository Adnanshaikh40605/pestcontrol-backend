from django.urls import path

from . import apis, operations_apis

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
    path('attendance/break/start/', operations_apis.BreakStartAPIView.as_view(), name='break-start'),
    path('attendance/break/end/', operations_apis.BreakEndAPIView.as_view(), name='break-end'),
    path('location/ping/', apis.LocationPingAPIView.as_view(), name='location-ping'),
    path('location/batch/', apis.LocationBatchAPIView.as_view(), name='location-batch'),

    # Visits
    path('visits/mine/', operations_apis.MyVisitsAPIView.as_view(), name='my-visits'),
    path('visits/', operations_apis.VisitListCreateAPIView.as_view(), name='visits'),
    path('visits/<int:visit_id>/checkin/', operations_apis.VisitCheckInAPIView.as_view(), name='visit-checkin'),
    path('visits/<int:visit_id>/checkout/', operations_apis.VisitCheckOutAPIView.as_view(), name='visit-checkout'),
    path('visits/<int:visit_id>/photos/', operations_apis.VisitPhotoUploadAPIView.as_view(), name='visit-photo'),

    # Tasks
    path('tasks/mine/', operations_apis.MyTasksAPIView.as_view(), name='my-tasks'),
    path('tasks/', operations_apis.TaskListCreateAPIView.as_view(), name='tasks'),
    path('tasks/<int:task_id>/status/', operations_apis.TaskStatusAPIView.as_view(), name='task-status'),
    path('tasks/<int:task_id>/comments/', operations_apis.TaskCommentAPIView.as_view(), name='task-comments'),

    # Leave
    path('leave/types/', operations_apis.LeaveTypesAPIView.as_view(), name='leave-types'),
    path('leave/balance/', operations_apis.LeaveBalanceAPIView.as_view(), name='leave-balance'),
    path('leave/apply/', operations_apis.LeaveApplyAPIView.as_view(), name='leave-apply'),
    path('leave/applications/', operations_apis.LeaveApplicationsAPIView.as_view(), name='leave-applications'),
    path('leave/applications/<int:application_id>/review/', operations_apis.LeaveReviewAPIView.as_view(), name='leave-review'),

    # Expenses
    path('expenses/categories/', operations_apis.ExpenseCategoriesAPIView.as_view(), name='expense-categories'),
    path('expenses/mine/', operations_apis.MyExpensesAPIView.as_view(), name='my-expenses'),
    path('expenses/', operations_apis.ExpenseListAPIView.as_view(), name='expenses'),
    path('expenses/<int:claim_id>/review/', operations_apis.ExpenseReviewAPIView.as_view(), name='expense-review'),
    path('expenses/<int:claim_id>/receipt/', operations_apis.ExpenseReceiptUploadAPIView.as_view(), name='expense-receipt'),
    path('geofences/', operations_apis.GeofenceListAPIView.as_view(), name='geofences'),

    # CRM dashboard
    path('live/', apis.LiveStaffAPIView.as_view(), name='live'),
    path('staff/', apis.StaffDirectoryAPIView.as_view(), name='staff-directory'),
    path('attendance/today/', apis.AttendanceTodayAPIView.as_view(), name='attendance-today'),
    path('attendance/report/', apis.AttendanceReportAPIView.as_view(), name='attendance-report'),
    path('location/history/<int:technician_id>/', apis.LocationHistoryAPIView.as_view(), name='location-history'),
    path('location/distance/', apis.DistanceReportAPIView.as_view(), name='distance-report'),
    path('settings/', apis.SettingsAPIView.as_view(), name='settings'),
]
