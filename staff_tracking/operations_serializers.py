from rest_framework import serializers

from .models import AttendanceBreak, AttendanceSession
from .operations_models import (
    ExpenseCategory,
    ExpenseClaim,
    ExpenseReceipt,
    FieldVisit,
    GeofenceZone,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    OrgHoliday,
    StaffTask,
    TaskComment,
)


class FieldVisitSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='profile.display_name', read_only=True)
    job_code = serializers.CharField(source='jobcard.code', read_only=True, allow_null=True)

    class Meta:
        model = FieldVisit
        fields = [
            'id', 'profile', 'staff_name', 'jobcard', 'job_code', 'title', 'client_name',
            'address', 'latitude', 'longitude', 'scheduled_at', 'status',
            'check_in_at', 'check_in_latitude', 'check_in_longitude',
            'check_out_at', 'notes', 'missed_reason', 'created_at',
        ]
        read_only_fields = [
            'check_in_at', 'check_in_latitude', 'check_in_longitude',
            'check_out_at', 'status', 'missed_reason',
        ]


class VisitCheckInSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    accuracy_m = serializers.FloatField(required=False, allow_null=True)


class VisitCheckOutSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class StaffTaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assigned_to.display_name', read_only=True)

    class Meta:
        model = StaffTask
        fields = [
            'id', 'title', 'description', 'assigned_to', 'assignee_name', 'priority', 'status',
            'due_at', 'completed_at', 'jobcard', 'field_visit', 'requires_gps_proof',
            'completion_latitude', 'completion_longitude', 'created_at',
        ]
        read_only_fields = ['completed_at', 'completion_latitude', 'completion_longitude']


class TaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StaffTask.Status.choices)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)


class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'body', 'author', 'profile', 'created_at']
        read_only_fields = ['author', 'profile', 'created_at']


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'code', 'default_days_per_year', 'requires_document', 'is_active']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    available = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'leave_type', 'leave_type_name', 'year', 'allocated', 'used',
            'pending', 'carry_forward', 'available',
        ]

    def get_available(self, obj) -> str:
        return str(obj.available)


class LeaveApplicationSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='profile.display_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            'id', 'profile', 'staff_name', 'leave_type', 'leave_type_name',
            'start_date', 'end_date', 'half_day', 'reason', 'status', 'days_count',
            'reviewer_comment', 'reviewed_at', 'created_at',
        ]
        read_only_fields = ['status', 'reviewer_comment', 'reviewed_at', 'days_count']


class LeaveApplySerializer(serializers.Serializer):
    leave_type_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=LeaveApplication.HalfDay.choices,
        default=LeaveApplication.HalfDay.FULL,
    )
    reason = serializers.CharField()


class LeaveReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    comment = serializers.CharField(required=False, allow_blank=True, default='')


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'code', 'requires_receipt_above', 'km_rate', 'is_active']


class ExpenseClaimSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='profile.display_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = ExpenseClaim
        fields = [
            'id', 'profile', 'staff_name', 'category', 'category_name', 'expense_date',
            'amount', 'gst_amount', 'description', 'status', 'distance_km',
            'jobcard', 'field_visit', 'reviewer_comment', 'reviewed_at', 'created_at',
        ]
        read_only_fields = ['status', 'reviewer_comment', 'reviewed_at', 'amount']


class ExpenseSubmitSerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    expense_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    use_gps_distance = serializers.BooleanField(default=False)


class ExpenseReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    comment = serializers.CharField(required=False, allow_blank=True, default='')


class AttendanceBreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceBreak
        fields = ['id', 'session', 'started_at', 'ended_at', 'latitude', 'longitude']


class OrgHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgHoliday
        fields = ['id', 'date', 'name']


class GeofenceZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeofenceZone
        fields = [
            'id', 'name', 'zone_type', 'latitude', 'longitude', 'radius_m', 'is_active',
        ]
