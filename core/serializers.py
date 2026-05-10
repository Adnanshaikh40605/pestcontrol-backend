from rest_framework import serializers
from .models import Client, Inquiry, JobCard, Renewal, Technician, CRMInquiry, Feedback, ActivityLog
from django.contrib.auth.models import User


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'full_name', 'mobile', 'email', 'state', 'city', 
            'address', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TechnicianSerializer(serializers.ModelSerializer):
    active_jobs = serializers.IntegerField(read_only=True)
    active_job_details = serializers.SerializerMethodField()
    phone = serializers.CharField(source='mobile', read_only=True)

    class Meta:
        model = Technician
        fields = [
            'id', 'name', 'mobile', 'phone', 'age', 'alternative_mobile', 
            'is_active', 'service_area', 'city', 'last_active', 'active_jobs', 'active_job_details', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_active_job_details(self, obj):
        # Return a list of basic info for current active jobs using values for efficiency
        return list(obj.jobcards.filter(status__iexact='On Process').values(
            'id', 'client__full_name', 'service_type'
        ))


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            'id', 'name', 'mobile', 'email', 'message', 
            'service_interest', 'state', 'city', 'status', 'is_read', 
            'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class JobCardSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='client.mobile', read_only=True)
    client_state = serializers.CharField(source='client.state', read_only=True)
    client_notes = serializers.CharField(source='client.notes', read_only=True, allow_null=True)
    
    technician_name = serializers.CharField(source='technician.name', read_only=True)
    technician_mobile = serializers.CharField(source='technician.mobile', read_only=True)
    
    # Nested client data for creation
    client_data = serializers.DictField(write_only=True, required=False, help_text="Client details for creation if client doesn't exist")

    schedule_datetime = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M", read_only=True)

    class Meta:
        model = JobCard
        fields = [
            'id', 'code', 'client', 'client_name', 'client_mobile', 'client_state', 'client_notes', 'client_data',
            'job_type', 'commercial_type', 'is_price_estimated', 'service_category', 'property_type', 'bhk_size', 'contract_duration', 'status', 'service_type', 'schedule_datetime', 
            'time_slot', 'state', 'city',
            'price', 'client_address',
            'payment_status', 'payment_mode', 'assigned_to', 'technician', 'technician_name', 'technician_mobile', 'next_service_date', 'service_cycle', 'max_cycle', 'parent_job', 'notes', 'is_paused', 'reference', 
            'extra_notes', 'cancellation_reason', 'removal_remarks', 
            'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done',
            'is_complaint_call', 'complaint_parent_booking', 'complaint_status', 'complaint_type', 'priority', 'complaint_note',
            'is_accepted', 'is_service_call', 'accepted_at', 'started_at', 'completed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Custom validation for JobCard creation with client data."""
        # Check if this is a creation (no instance yet)
        is_create = self.instance is None
        
        # If client_data is provided, validate it
        if is_create and 'client_data' in data and data['client_data']:
            client_data = data['client_data']
            
            # Validate required client fields
            # Note: full_name is optional when client already exists (will be determined by get_or_create)
            # mobile is always required
            required_client_fields = ['mobile']
            for field in required_client_fields:
                if not client_data.get(field):
                    raise serializers.ValidationError({
                        'client_data': {field: f"{field.replace('_', ' ').title()} is required."}
                    })
            
            # full_name is only required if provided (for new client creation)
            # If not provided, backend will use existing client's name
            if 'full_name' in client_data and not client_data.get('full_name'):
                raise serializers.ValidationError({
                    'client_data': {'full_name': 'Full name cannot be empty if provided.'}
                })
            
            # Validate mobile number format
            mobile = client_data.get('mobile', '')
            if mobile and not mobile.isdigit() or len(mobile) != 10:
                raise serializers.ValidationError({
                    'client_data': {'mobile': 'Mobile number must be exactly 10 digits.'}
                })
        
        # Business rule: Cancellation reason validation
        status = data.get('status')
        # If updating, check the current status if not provided in data
        if status is None and self.instance:
            status = self.instance.status
            
        if status == 'Cancelled':
            cancellation_reason = data.get('cancellation_reason')
            # If updating, check the current reason if not provided in data
            if cancellation_reason is None and self.instance:
                cancellation_reason = self.instance.cancellation_reason
                
            if not cancellation_reason or not cancellation_reason.strip():
                raise serializers.ValidationError({'cancellation_reason': 'Cancellation reason is required when status is Cancelled.'})
            
            # Min 4 characters
            if len(cancellation_reason.strip()) < 4:
                raise serializers.ValidationError({'cancellation_reason': 'Reason must be at least 4 characters.'})
            
            # No special characters (alphabets, numbers, spaces only)
            import re
            if not re.match(r'^[a-zA-Z0-9\s]*$', cancellation_reason):
                raise serializers.ValidationError({'cancellation_reason': 'Special characters are not allowed in the cancellation reason.'})
        
        # Business rule: Technician removal validation (On Process -> Pending)
        if status == 'Pending' and self.instance and self.instance.status in ['On Process', 'Confirmed']:
            # If the current status is assigned, but we are moving back to Pending, require remarks
            removal_remarks = data.get('removal_remarks')
            
            # Note: technician being None/empty also indicates removal if it was assigned
            if not removal_remarks or not removal_remarks.strip():
                raise serializers.ValidationError({'removal_remarks': 'Removal remarks are required when removing a technician.'})
            
            if len(removal_remarks.strip()) < 4:
                raise serializers.ValidationError({'removal_remarks': 'Remarks must be at least 4 characters.'})
        
        return data


class RenewalSerializer(serializers.ModelSerializer):
    jobcard_code = serializers.CharField(source='jobcard.code', read_only=True)
    client_name = serializers.CharField(source='jobcard.client.full_name', read_only=True)
    is_paused = serializers.BooleanField(source='jobcard.is_paused', read_only=True)
    urgency_color = serializers.SerializerMethodField()

    class Meta:
        model = Renewal
        fields = [
            'id', 'jobcard', 'jobcard_code', 'client_name', 'is_paused',
            'due_date', 'status', 'renewal_type', 'urgency_level', 'urgency_color',
            'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'urgency_color']
    
    def get_urgency_color(self, obj):
        """Return color code based on urgency level."""
        color_map = {
            'High': '#ff4444',    # Red
            'Medium': '#ffaa00',  # Yellow/Orange
            'Normal': '#44aa44'   # Green
        }
        return color_map.get(obj.urgency_level, '#44aa44')


class CRMInquirySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = CRMInquiry
        fields = [
            'id', 'name', 'mobile', 'location', 'pest_type', 'remark', 
            'inquiry_date', 'inquiry_time', 'status', 'created_by', 'created_by_name',
            'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class FeedbackSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='booking.client.full_name', read_only=True)
    technician_name = serializers.CharField(source='booking.technician.name', read_only=True)
    booking_code = serializers.CharField(source='booking.code', read_only=True)
    service_name = serializers.CharField(source='booking.service_type', read_only=True)
    service_date = serializers.DateTimeField(source='booking.schedule_datetime', read_only=True)

    class Meta:
        model = Feedback
        fields = [
            'id', 'booking', 'booking_code', 'client_name', 'technician_name', 
            'service_name', 'service_date', 'rating', 'remark', 
            'technician_behavior', 'feedback_type', 'token', 'created_at'
        ]
        read_only_fields = ['id', 'token', 'created_at', 'feedback_type']


class TechnicianPerformanceSerializer(serializers.ModelSerializer):
    assigned_count = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    pending_count = serializers.IntegerField(read_only=True)
    on_process_count = serializers.IntegerField(read_only=True)
    service_calls_count = serializers.IntegerField(read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    feedback_count = serializers.IntegerField(read_only=True)
    completion_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Technician
        fields = [
            'id', 'name', 'mobile', 'is_active', 'service_area', 'city', 'last_active',
            'assigned_count', 'completed_count', 'pending_count', 'on_process_count',
            'service_calls_count', 'total_revenue', 'avg_rating', 'feedback_count',
            'completion_rate'
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='user.get_full_name', read_only=True)
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M", read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'staff_name', 'action', 'booking_id', 'details', 'created_at']


class StaffSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name')
    mobile = serializers.CharField(source='username')
    role = serializers.ChoiceField(choices=['Super Admin', 'Staff'], write_only=True, required=False)
    role_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'mobile', 'role', 'role_display', 'password', 'is_active', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'date_joined': {'read_only': True}
        }

    def get_role_display(self, obj):
        if obj.is_superuser:
            return 'Super Admin'
        return 'Staff'

    def validate_mobile(self, value):
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(username=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("A staff member with this mobile number already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        role = validated_data.pop('role', 'Staff')
        validated_data['is_staff'] = True
        validated_data['is_superuser'] = (role == 'Super Admin')
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        role = validated_data.pop('role', None)
        if role is not None:
            instance.is_superuser = (role == 'Super Admin')
            instance.save()
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
