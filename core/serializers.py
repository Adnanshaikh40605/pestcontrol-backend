from rest_framework import serializers
from .models import Client, Inquiry, JobCard, Renewal, DeviceToken, NotificationLog, NotificationSubscription


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'full_name', 'mobile', 'email', 'city', 
            'address', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            'id', 'name', 'mobile', 'email', 'message', 
            'service_interest', 'city', 'status', 'is_read', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class JobCardSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='client.mobile', read_only=True)
    client_city = serializers.CharField(source='client.city', read_only=True)
    
    # Nested client data for creation
    client_data = serializers.DictField(write_only=True, required=False, help_text="Client details for creation if client doesn't exist")

    class Meta:
        model = JobCard
        fields = [
            'id', 'code', 'client', 'client_name', 'client_mobile', 'client_city', 'client_data',
            'job_type', 'contract_duration', 'status', 'service_type', 'schedule_date', 
            'technician_name', 'price', 
            'payment_status', 'next_service_date', 'notes', 'is_paused', 'reference', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Custom validation for JobCard creation with client data."""
        # If client_data is provided, validate it
        if 'client_data' in data and data['client_data']:
            client_data = data['client_data']
            
            # Validate required client fields
            required_client_fields = ['full_name', 'mobile', 'city']
            for field in required_client_fields:
                if not client_data.get(field):
                    raise serializers.ValidationError({
                        'client_data': {field: f"{field.replace('_', ' ').title()} is required for client creation."}
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


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'token', 'device_type', 'user_agent', 'is_active', 
            'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_used', 'created_at', 'updated_at']
    
    def validate_token(self, value):
        """Validate device token format."""
        if not value or len(value.strip()) < 50:
            raise serializers.ValidationError("Device token appears to be invalid or too short.")
        return value.strip()


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'title', 'body', 'notification_type', 'status', 
            'target_tokens', 'topic', 'data_payload', 'success_count', 
            'failure_count', 'error_message', 'firebase_message_id', 
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'success_count', 'failure_count', 'error_message', 
            'firebase_message_id', 'created_at', 'updated_at'
        ]


class NotificationSubscriptionSerializer(serializers.ModelSerializer):
    device_token_info = serializers.CharField(source='device_token.token', read_only=True)
    device_type = serializers.CharField(source='device_token.device_type', read_only=True)
    
    class Meta:
        model = NotificationSubscription
        fields = [
            'id', 'device_token', 'device_token_info', 'device_type', 
            'topic', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_topic(self, value):
        """Validate topic name format."""
        import re
        if not re.match(r'^[a-z0-9_-]+$', value.lower()):
            raise serializers.ValidationError(
                "Topic name can only contain lowercase letters, numbers, hyphens, and underscores."
            )
        return value.lower()


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending notifications."""
    title = serializers.CharField(max_length=255, help_text="Notification title")
    body = serializers.CharField(help_text="Notification body/message")
    device_tokens = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of device tokens to send notification to"
    )
    topic = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Topic name for topic notifications"
    )
    data = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        help_text="Additional data payload"
    )
    image_url = serializers.URLField(
        required=False,
        help_text="URL of notification image"
    )
    click_action = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Action to perform when notification is clicked"
    )
    
    def validate(self, data):
        """Validate that either device_tokens or topic is provided."""
        if not data.get('device_tokens') and not data.get('topic'):
            raise serializers.ValidationError(
                "Either device_tokens or topic must be provided."
            )
        return data


class SubscribeToTopicSerializer(serializers.Serializer):
    """Serializer for subscribing to topics."""
    device_tokens = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of device tokens to subscribe"
    )
    topic = serializers.CharField(
        max_length=100,
        help_text="Topic name to subscribe to"
    )
    
    def validate_topic(self, value):
        """Validate topic name format."""
        import re
        if not re.match(r'^[a-z0-9_-]+$', value.lower()):
            raise serializers.ValidationError(
                "Topic name can only contain lowercase letters, numbers, hyphens, and underscores."
            )
        return value.lower()


