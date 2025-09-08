from rest_framework import serializers
from .models import Client, Inquiry, JobCard, Renewal


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

    class Meta:
        model = JobCard
        fields = [
            'id', 'code', 'client', 'client_name', 'client_mobile', 'client_city',
            'job_type', 'contract_duration', 'status', 'service_type', 'schedule_date', 
            'technician_name', 'price_subtotal', 'tax_percent', 'grand_total', 
            'payment_status', 'next_service_date', 'notes', 'is_paused', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'grand_total', 'created_at', 'updated_at']


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


