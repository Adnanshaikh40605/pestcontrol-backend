from rest_framework import serializers
from .models import Client, Inquiry, JobCard, Renewal, Technician, CRMInquiry, Feedback, ActivityLog, Reminder, Country, State, City, Location, Quotation, QuotationItem, QuotationScope, QuotationPaymentTerm, QuotationHistory
from django.contrib.auth.models import User


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'is_active']


class StateSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = State
        fields = ['id', 'country', 'country_name', 'name', 'is_active']


class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True)

    class Meta:
        model = City
        fields = ['id', 'state', 'state_name', 'name', 'is_active']


class LocationSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'city', 'city_name', 'name', 'is_active']


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
    created_by_name = serializers.SerializerMethodField()
    converted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            'id', 'name', 'mobile', 'email', 'message', 
            'service_interest', 'state', 'city', 'status', 'is_read', 
            'premise_type', 'premise_size', 'pest_problems', 
            'estimated_price', 'is_inspection_required', 'service_frequency',
            'remark',
            'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done',
            'created_by', 'created_by_name', 'converted_by', 'converted_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'converted_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "Website"

    def get_converted_by_name(self, obj):
        if obj.converted_by:
            return obj.converted_by.get_full_name() or obj.converted_by.username
        return None


class JobCardSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='client.mobile', read_only=True)
    client_state = serializers.CharField(source='client.state', read_only=True)
    client_notes = serializers.CharField(source='client.notes', read_only=True, allow_null=True)
    
    technician_name = serializers.CharField(source='technician.name', read_only=True)
    technician_mobile = serializers.CharField(source='technician.mobile', read_only=True)
    
    # Master Location Display Names
    master_country_name = serializers.CharField(source='master_country.name', read_only=True)
    master_state_name = serializers.CharField(source='master_state.name', read_only=True)
    master_city_name = serializers.CharField(source='master_city.name', read_only=True)
    master_location_name = serializers.CharField(source='master_location.name', read_only=True)

    created_by_name = serializers.SerializerMethodField()
    on_process_by_name = serializers.SerializerMethodField()
    done_by_name = serializers.SerializerMethodField()

    # Nested client data for creation
    client_data = serializers.DictField(write_only=True, required=False, help_text="Client details for creation if client doesn't exist")

    schedule_datetime = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M", read_only=True)

    is_accepted = serializers.BooleanField(read_only=True)
    is_service_call = serializers.BooleanField(read_only=True)
    
    partner_name = serializers.CharField(source='partner.full_name', read_only=True)

    class Meta:
        model = JobCard
        fields = [
            'id', 'code', 'client', 'client_name', 'client_mobile', 'client_state', 'client_notes', 'client_data',
            'job_type', 'commercial_type', 'is_price_estimated', 'service_category', 'property_type', 'bhk_size', 'contract_duration', 'status', 'service_type', 'schedule_datetime', 
            'time_slot', 'state', 'city',
            'master_country', 'master_country_name', 'master_state', 'master_state_name', 'master_city', 'master_city_name', 'master_location', 'master_location_name', 'full_address',
            'price', 'price_display', 'client_address',
            'payment_status', 'payment_mode', 'assigned_to', 'technician', 'technician_name', 'technician_mobile', 
            'partner', 'partner_name', 'partner_status',
            'next_service_date', 'service_cycle', 'max_cycle', 'parent_job', 'notes', 'is_paused', 'reference', 
            'extra_notes', 'cancellation_reason', 'removal_remarks', 
            'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done',
            'is_complaint_call', 'complaint_parent_booking', 'complaint_status', 'complaint_type', 'priority', 'complaint_note',
            'is_accepted', 'is_service_call', 'accepted_at', 'started_at', 'completed_at',
            'is_amc_main_booking', 'is_followup_visit', 'included_in_amc',
            'created_by', 'created_by_name', 'on_process_by', 'on_process_by_name', 'done_by', 'done_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'created_by', 'on_process_by', 'done_by', 'created_at', 'updated_at']

    price_display = serializers.SerializerMethodField()
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "System"

    def get_on_process_by_name(self, obj):
        if obj.on_process_by:
            return obj.on_process_by.get_full_name() or obj.on_process_by.username
        return None

    def get_done_by_name(self, obj):
        if obj.done_by:
            return obj.done_by.get_full_name() or obj.done_by.username
        return None

    def get_price_display(self, obj):
        if obj.booking_type == JobCard.BookingType.AMC_FOLLOWUP or obj.included_in_amc:
            return "Included in AMC"
        if obj.booking_type == JobCard.BookingType.COMPLAINT_CALL:
            return "Free (Complaint)"
        if obj.booking_type == JobCard.BookingType.SERVICE_CALL and obj.service_cycle > 1:
             return "Included in Service"
        return obj.price
    
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
        
        # Business rule: Reference validation
        reference = data.get('reference')
        if reference is None and self.instance:
            reference = self.instance.reference
            
        if not reference or not reference.strip():
            # If it's an update and reference is missing/empty, default to 'Other'
            # to avoid blocking updates (like cancellation) for older records.
            if self.instance:
                data['reference'] = 'Other'
            else:
                raise serializers.ValidationError({'reference': 'Reference is required for all bookings.'})

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
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Renewal
        fields = [
            'id', 'jobcard', 'jobcard_code', 'client_name', 'is_paused',
            'due_date', 'status', 'renewal_type', 'urgency_level', 'urgency_color',
            'remarks', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'urgency_color']
    
    def get_urgency_color(self, obj):
        """Return color code based on urgency level."""
        color_map = {
            'High': '#ff4444',    # Red
            'Medium': '#ffaa00',  # Yellow/Orange
            'Normal': '#44aa44'   # Green
        }
        return color_map.get(obj.urgency_level, '#44aa44')


class CRMInquirySerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    converted_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CRMInquiry
        fields = [
            'id', 'name', 'mobile', 'location', 'pest_type', 'remark', 'service_frequency',
            'inquiry_date', 'inquiry_time', 'status', 'created_by', 'created_by_name',
            'converted_by', 'converted_by_name',
            'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'converted_by']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "System"

    def get_converted_by_name(self, obj):
        if obj.converted_by:
            return obj.converted_by.get_full_name() or obj.converted_by.username
        return None


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


class ReminderSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M", read_only=True)

    class Meta:
        model = Reminder
        fields = [
            'id', 'inquiry_type', 'inquiry_id', 'customer_name', 'mobile_number',
            'reminder_date', 'reminder_time', 'note', 'created_by', 'created_by_name',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "System"


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


class QuotationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationItem
        fields = ['id', 'service_name', 'frequency', 'quantity', 'rate', 'total', 'description']


class QuotationScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationScope
        fields = ['id', 'title', 'content']


class QuotationPaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationPaymentTerm
        fields = ['id', 'term', 'description']


class QuotationHistorySerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M", read_only=True)

    class Meta:
        model = QuotationHistory
        fields = ['id', 'action', 'details', 'performed_by', 'performed_by_name', 'created_at']


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True)
    scopes = QuotationScopeSerializer(many=True, required=False)
    payment_terms = QuotationPaymentTermSerializer(many=True, required=False)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'invoice_no', 'reference_no',
            'customer_name', 'mobile', 'email', 'address', 'city', 'state', 'pincode',
            'contact_person', 'company_name', 'quotation_type', 'status',
            'total_amount', 'discount', 'tax_amount', 'grand_total',
            'is_amc', 'visit_count', 'contract_amount',
            'expiry_date', 'created_by', 'created_by_name', 'license_number',
            'notes', 'terms_and_conditions',
            'items', 'scopes', 'payment_terms', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'quotation_no', 'invoice_no', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        scopes_data = validated_data.pop('scopes', [])
        payment_terms_data = validated_data.pop('payment_terms', [])
        
        quotation = Quotation.objects.create(**validated_data)
        
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)
            
        for scope_data in scopes_data:
            QuotationScope.objects.create(quotation=quotation, **scope_data)
            
        for term_data in payment_terms_data:
            QuotationPaymentTerm.objects.create(quotation=quotation, **term_data)
            
        # Log creation in history
        QuotationHistory.objects.create(
            quotation=quotation,
            action="Quotation Created",
            details=f"Quotation {quotation.quotation_no} created by {quotation.created_by.username if quotation.created_by else 'System'}",
            performed_by=quotation.created_by
        )
        
        return quotation

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        scopes_data = validated_data.pop('scopes', None)
        payment_terms_data = validated_data.pop('payment_terms', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                QuotationItem.objects.create(quotation=instance, **item_data)
                
        # Update scopes if provided
        if scopes_data is not None:
            instance.scopes.all().delete()
            for scope_data in scopes_data:
                QuotationScope.objects.create(quotation=instance, **scope_data)
                
        # Update payment terms if provided
        if payment_terms_data is not None:
            instance.payment_terms.all().delete()
            for term_data in payment_terms_data:
                QuotationPaymentTerm.objects.create(quotation=instance, **term_data)
                
        # Log update in history
        QuotationHistory.objects.create(
            quotation=instance,
            action="Quotation Updated",
            details=f"Quotation {instance.quotation_no} updated",
            performed_by=self.context.get('request').user if 'request' in self.context else None
        )
        
        return instance
