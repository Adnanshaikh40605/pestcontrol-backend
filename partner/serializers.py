from rest_framework import serializers
from .models import Partner, PartnerEarning, PartnerRating
from core.models import JobCard


class PartnerSerializer(serializers.ModelSerializer):
    """Serializer for Partner profile data."""
    class Meta:
        model = Partner
        fields = [
            'id', 'full_name', 'mobile', 'role', 'profile_image',
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PartnerRegisterSerializer(serializers.Serializer):
    """Serializer for partner registration."""
    full_name = serializers.CharField(max_length=255)
    mobile = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=6, write_only=True)
    role = serializers.ChoiceField(
        choices=['technician', 'technician_admin'],
        default='technician'
    )

    def validate_mobile(self, value):
        if Partner.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("A partner with this mobile number already exists.")
        return value

    def create(self, validated_data):
        partner = Partner(
            full_name=validated_data['full_name'],
            mobile=validated_data['mobile'],
            role=validated_data.get('role', 'technician'),
        )
        partner.set_password(validated_data['password'])
        partner.save()
        return partner


class PartnerLoginSerializer(serializers.Serializer):
    """Serializer for partner login."""
    mobile = serializers.CharField()
    password = serializers.CharField(write_only=True)


class PartnerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for partner profile update."""
    class Meta:
        model = Partner
        fields = [
            'full_name', 'profile_image',
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
        ]


class PartnerFCMSerializer(serializers.Serializer):
    """Serializer for updating FCM push token."""
    fcm_token = serializers.CharField()


# ──────────────────────────────────────────────
# Booking Serializers
# ──────────────────────────────────────────────

class PartnerBookingListSerializer(serializers.ModelSerializer):
    """Compact booking serializer for list views (Available / Accepted)."""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='client.mobile', read_only=True)
    location_display = serializers.SerializerMethodField()
    priority_label = serializers.CharField(source='priority', read_only=True)
    booking_tag = serializers.SerializerMethodField()

    class Meta:
        model = JobCard
        fields = [
            'id', 'code', 'service_type', 'service_category', 'booking_type',
            'client_name', 'client_mobile',
            'client_address', 'location_display',
            'schedule_datetime', 'time_slot',
            'priority', 'priority_label', 'booking_tag',
            'status', 'partner_status',
            'is_complaint_call', 'complaint_type',
            'property_type', 'bhk_size',
            'price', 'payment_status',
        ]

    def get_location_display(self, obj):
        """Returns a user-friendly location string."""
        parts = []
        if obj.client_address:
            parts.append(obj.client_address)
        if obj.master_location:
            parts.append(obj.master_location.name)
        if obj.master_city:
            parts.append(obj.master_city.name)
        return ", ".join(parts) if parts else obj.city or ""

    def get_booking_tag(self, obj):
        """Returns a tag label for display on the card (e.g., AMC VISIT, High Priority)."""
        if obj.booking_type == JobCard.BookingType.AMC_FOLLOWUP:
            return "AMC VISIT"
        if obj.is_complaint_call:
            return "COMPLAINT"
        if obj.priority == JobCard.Priority.HIGH:
            return "HIGH PRIORITY"
        return "STANDARD"


class PartnerBookingDetailSerializer(serializers.ModelSerializer):
    """Detailed booking serializer for the detail screen."""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_mobile = serializers.CharField(source='client.mobile', read_only=True)
    client_notes = serializers.CharField(source='client.notes', read_only=True, allow_null=True)
    location_display = serializers.SerializerMethodField()
    booking_tag = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()

    class Meta:
        model = JobCard
        fields = [
            'id', 'code',
            # Customer
            'client_name', 'client_mobile', 'client_address', 'client_notes',
            'location_display', 'city_name',
            # Property
            'property_type', 'bhk_size', 'commercial_type',
            # Service
            'service_type', 'service_category', 'booking_type', 'booking_tag',
            'is_complaint_call', 'complaint_type', 'complaint_note',
            # Schedule
            'schedule_datetime', 'time_slot',
            # Payment
            'price', 'price_display', 'payment_status', 'payment_mode',
            # Status
            'status', 'partner_status', 'priority',
            # Timestamps
            'accepted_at', 'started_at', 'completed_at',
            # Notes
            'notes', 'extra_notes',
        ]

    def get_location_display(self, obj):
        parts = []
        if obj.client_address:
            parts.append(obj.client_address)
        if obj.master_location:
            parts.append(obj.master_location.name)
        if obj.master_city:
            parts.append(obj.master_city.name)
        return ", ".join(parts) if parts else obj.city or ""

    def get_city_name(self, obj):
        if obj.master_city:
            return obj.master_city.name
        return obj.city or ""

    def get_booking_tag(self, obj):
        if obj.booking_type == JobCard.BookingType.AMC_FOLLOWUP:
            return "AMC VISIT"
        if obj.is_complaint_call:
            return "COMPLAINT"
        if obj.priority == JobCard.Priority.HIGH:
            return "HIGH PRIORITY"
        return "STANDARD"

    def get_price_display(self, obj):
        if hasattr(obj, 'price_display') and obj.price_display:
            return obj.price_display
        if obj.included_in_amc:
            return "Included in AMC"
        if obj.is_complaint_call:
            return "Free (Complaint)"
        return f"₹{obj.price}" if obj.price else "TBD"


class PartnerCompleteBookingSerializer(serializers.Serializer):
    """Serializer for completing a booking (End Service)."""
    payment_mode = serializers.ChoiceField(
        choices=['Cash', 'Online'],
        help_text="Payment mode selected by the customer at the time of service"
    )


class PartnerEarningSerializer(serializers.ModelSerializer):
    """Serializer for earnings history."""
    job_code = serializers.CharField(source='job.code', read_only=True)
    service_type = serializers.CharField(source='job.service_type', read_only=True)
    completed_at = serializers.DateTimeField(source='job.completed_at', read_only=True)

    class Meta:
        model = PartnerEarning
        fields = ['id', 'job_code', 'service_type', 'amount', 'completed_at', 'created_at']


class PartnerProfileStatsSerializer(serializers.Serializer):
    """Serializer for the Profile tab statistics."""
    partner = PartnerSerializer()
    total_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    accepted_jobs = serializers.IntegerField()
    available_jobs = serializers.IntegerField()
    service_calls = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
