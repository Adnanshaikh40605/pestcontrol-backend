from django.contrib import admin

from .models import (
    AttendanceSession,
    LocationPing,
    TrackingConsent,
    TrackingProfile,
    TrackingSettings,
)


@admin.register(TrackingSettings)
class TrackingSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'ping_interval_moving_seconds',
        'shift_start_time',
        'shift_end_time',
        'location_retention_days',
    )


@admin.register(TrackingProfile)
class TrackingProfileAdmin(admin.ModelAdmin):
    list_display = ('technician', 'is_active', 'tracking_enabled', 'created_at')
    list_filter = ('is_active', 'tracking_enabled')
    search_fields = ('technician__name', 'technician__mobile')


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'date', 'status', 'check_in_at', 'check_out_at', 'total_distance_km')
    list_filter = ('status', 'date')
    date_hierarchy = 'date'


@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    list_display = ('profile', 'recorded_at', 'latitude', 'longitude', 'battery_percent')
    date_hierarchy = 'recorded_at'


@admin.register(TrackingConsent)
class TrackingConsentAdmin(admin.ModelAdmin):
    list_display = ('profile', 'consented_at', 'consent_version')
