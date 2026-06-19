from rest_framework import serializers

from .models import (
    AttendanceSession,
    LocationPing,
    TrackingProfile,
    TrackingSettings,
)


class TrackingLoginSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)


class GPSPointSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    accuracy_m = serializers.FloatField(required=False, allow_null=True)
    altitude_m = serializers.FloatField(required=False, allow_null=True)
    speed_mps = serializers.FloatField(required=False, allow_null=True)
    heading = serializers.FloatField(required=False, allow_null=True)
    battery_percent = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=100)
    recorded_at = serializers.DateTimeField(required=False)
    is_moving = serializers.BooleanField(required=False, default=True)


class LocationPingBatchSerializer(serializers.Serializer):
    pings = GPSPointSerializer(many=True)


class TrackingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingSettings
        fields = [
            'ping_interval_moving_seconds',
            'ping_interval_idle_seconds',
            'location_retention_days',
            'shift_start_time',
            'shift_end_time',
            'grace_minutes',
        ]


class TrackingProfileSerializer(serializers.ModelSerializer):
    technician_id = serializers.IntegerField(source='technician.id', read_only=True)
    name = serializers.CharField(source='technician.name', read_only=True)
    mobile = serializers.CharField(source='technician.mobile', read_only=True)
    city = serializers.CharField(source='technician.city', read_only=True, allow_null=True)

    class Meta:
        model = TrackingProfile
        fields = [
            'id',
            'technician_id',
            'name',
            'mobile',
            'city',
            'is_active',
            'tracking_enabled',
        ]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='profile.display_name', read_only=True)
    technician_id = serializers.IntegerField(source='profile.technician_id', read_only=True)
    is_late = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            'id',
            'technician_id',
            'staff_name',
            'date',
            'status',
            'check_in_at',
            'check_out_at',
            'check_in_latitude',
            'check_in_longitude',
            'check_out_latitude',
            'check_out_longitude',
            'total_distance_km',
            'is_late',
        ]

    def get_is_late(self, obj):
        from .services import is_late_checkin
        return is_late_checkin(obj.check_in_at)


class LocationPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPing
        fields = [
            'id',
            'latitude',
            'longitude',
            'accuracy_m',
            'speed_mps',
            'battery_percent',
            'recorded_at',
            'is_moving',
        ]


class LiveStaffSerializer(serializers.Serializer):
    profile_id = serializers.IntegerField()
    technician_id = serializers.IntegerField()
    name = serializers.CharField()
    mobile = serializers.CharField()
    city = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, allow_null=True)
    last_ping_at = serializers.DateTimeField(allow_null=True)
    battery_percent = serializers.IntegerField(allow_null=True)
    check_in_at = serializers.DateTimeField(allow_null=True)
    distance_today_km = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)


class MeStatusSerializer(serializers.Serializer):
    profile = TrackingProfileSerializer()
    has_consent = serializers.BooleanField()
    is_checked_in = serializers.BooleanField()
    active_session = AttendanceSessionSerializer(allow_null=True)
    settings = TrackingSettingsSerializer()
    last_ping = LocationPingSerializer(allow_null=True)
