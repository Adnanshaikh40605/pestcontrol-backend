from rest_framework import serializers
from django.core.validators import RegexValidator
from .models import Client, Inquiry, JobCard, Renewal
from django.db import models


class ClientSerializer(serializers.ModelSerializer):
    """Serializer for Client model with enhanced validation."""
    
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_mobile(self, value):
        """Validate mobile number format."""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
        return value
    
    def validate_email(self, value):
        """Validate email uniqueness if provided."""
        if value:
            if Client.objects.filter(email=value).exists():
                raise serializers.ValidationError("A client with this email already exists.")
        return value


class InquirySerializer(serializers.ModelSerializer):
    """Serializer for Inquiry model with enhanced validation."""
    
    class Meta:
        model = Inquiry
        fields = '__all__'
        read_only_fields = ('status', 'created_at', 'updated_at')
    
    def validate_mobile(self, value):
        """Validate mobile number format."""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
        return value
    
    def validate_email(self, value):
        """Validate email uniqueness if provided."""
        if value:
            if Inquiry.objects.filter(email=value).exists():
                raise serializers.ValidationError("An inquiry with this email already exists.")
        return value


class JobCardSerializer(serializers.ModelSerializer):
    """Serializer for JobCard model with nested client information."""
    
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='client.mobile', read_only=True)
    client_city = serializers.CharField(source='client.city', read_only=True)
    client_email = serializers.EmailField(source='client.email', read_only=True)
    
    class Meta:
        model = JobCard
        fields = '__all__'
        read_only_fields = ('code', 'grand_total', 'created_at', 'updated_at')
    
    def validate_schedule_date(self, value):
        """Validate schedule date is not in the past."""
        # Removed past date validation to support historical data
        return value
    
    def validate_price_subtotal(self, value):
        """Validate price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value
    
    def validate_tax_percent(self, value):
        """Validate tax percentage is between 0 and 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Tax percentage must be between 0 and 100.")
        return value
    
    def validate_next_service_date(self, value):
        """Validate next service date is after schedule date."""
        schedule_date = self.initial_data.get('schedule_date')
        if value and schedule_date and value <= schedule_date:
            raise serializers.ValidationError("Next service date must be after the schedule date.")
        return value


class RenewalSerializer(serializers.ModelSerializer):
    """Serializer for Renewal model with nested job card information."""
    
    jobcard_code = serializers.CharField(source='jobcard.code', read_only=True)
    client_name = serializers.CharField(source='jobcard.client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='jobcard.client.mobile', read_only=True)
    service_type = serializers.CharField(source='jobcard.service_type', read_only=True)
    
    class Meta:
        model = Renewal
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_due_date(self, value):
        """Validate due date is not in the past."""
        # Removed past date validation to support historical data
        return value


class ClientDetailSerializer(ClientSerializer):
    """Detailed client serializer with job card statistics."""
    
    total_job_cards = serializers.SerializerMethodField()
    completed_job_cards = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    
    class Meta(ClientSerializer.Meta):
        fields = list(ClientSerializer.Meta.fields) + ['total_job_cards', 'completed_job_cards', 'total_spent']
    
    def get_total_job_cards(self, obj):
        """Get total number of job cards for the client."""
        return obj.job_cards.count()
    
    def get_completed_job_cards(self, obj):
        """Get number of completed job cards for the client."""
        return obj.job_cards.filter(status='Done').count()
    
    def get_total_spent(self, obj):
        """Get total amount spent by the client."""
        return obj.job_cards.filter(payment_status='Paid').aggregate(
            total=models.Sum('grand_total')
        )['total'] or 0


class JobCardDetailSerializer(JobCardSerializer):
    """Detailed job card serializer with client and renewal information."""
    
    client_details = ClientSerializer(source='client', read_only=True)
    renewals = RenewalSerializer(many=True, read_only=True)
    
    class Meta(JobCardSerializer.Meta):
        fields = list(JobCardSerializer.Meta.fields) + ['client_details', 'renewals']


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics."""
    
    total_clients = serializers.IntegerField()
    total_job_cards = serializers.IntegerField()
    pending_job_cards = serializers.IntegerField()
    completed_job_cards = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    upcoming_renewals = serializers.IntegerField()
    overdue_renewals = serializers.IntegerField()
    new_inquiries = serializers.IntegerField()