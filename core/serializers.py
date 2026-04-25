from rest_framework import serializers
from .models import Client, Inquiry, JobCard, Renewal, Technician, CRMInquiry


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'full_name', 'mobile', 'email', 'state', 'city', 
            'address', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technician
        fields = [
            'id', 'name', 'mobile', 'age', 'alternative_mobile', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            'id', 'name', 'mobile', 'email', 'message', 
            'service_interest', 'state', 'city', 'status', 'is_read', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class JobCardSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='client.mobile', read_only=True)
    client_city = serializers.CharField(source='client.city', read_only=True)
    client_state = serializers.CharField(source='client.state', read_only=True)
    client_notes = serializers.CharField(source='client.notes', read_only=True, allow_null=True)
    
    technician_name = serializers.CharField(source='technician.name', read_only=True)
    
    # Nested client data for creation
    client_data = serializers.DictField(write_only=True, required=False, help_text="Client details for creation if client doesn't exist")

    class Meta:
        model = JobCard
        fields = [
            'id', 'code', 'client', 'client_name', 'client_mobile', 'client_state', 'client_city', 'client_notes', 'client_data',
            'job_type', 'service_category', 'property_type', 'bhk_size', 'contract_duration', 'status', 'service_type', 'schedule_date', 
            'time_slot', 'state', 'city',
            'price', 'client_address',
            'payment_status', 'assigned_to', 'technician', 'technician_name', 'next_service_date', 'notes', 'is_paused', 'reference', 
            'extra_notes', 'created_at', 'updated_at'
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
            # mobile, state and city are always required
            required_client_fields = ['mobile', 'state', 'city']
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
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
