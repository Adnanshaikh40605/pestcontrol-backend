from datetime import time
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel, Technician


class TrackingSettings(BaseModel):
    """Singleton org-wide tracking configuration for Pest Control 99."""

    ping_interval_moving_seconds = models.PositiveIntegerField(default=30)
    ping_interval_idle_seconds = models.PositiveIntegerField(default=300)
    location_retention_days = models.PositiveIntegerField(default=90)
    shift_start_time = models.TimeField(default=time(9, 0))
    shift_end_time = models.TimeField(default=time(18, 0))
    grace_minutes = models.PositiveIntegerField(default=15)

    class Meta:
        verbose_name = 'Tracking Settings'
        verbose_name_plural = 'Tracking Settings'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TrackingProfile(BaseModel):
    """Links a trackable field staff member to tracking data."""

    technician = models.OneToOneField(
        Technician,
        on_delete=models.CASCADE,
        related_name='tracking_profile',
    )
    partner = models.OneToOneField(
        'partner.Partner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tracking_profile',
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tracking_profile',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    tracking_enabled = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Tracking Profile'
        verbose_name_plural = 'Tracking Profiles'

    def __str__(self):
        return f'Tracking: {self.technician.name}'

    @property
    def display_name(self):
        return self.technician.name


class TrackingConsent(BaseModel):
    """Employee consent for GPS tracking (India compliance)."""

    profile = models.OneToOneField(
        TrackingProfile,
        on_delete=models.CASCADE,
        related_name='consent',
    )
    consented_at = models.DateTimeField(default=timezone.now)
    consent_version = models.CharField(max_length=20, default='1.0')
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'Tracking Consent'
        verbose_name_plural = 'Tracking Consents'


class AttendanceSession(BaseModel):
    """Daily check-in / check-out session for a tracked staff member."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'

    profile = models.ForeignKey(
        TrackingProfile,
        on_delete=models.CASCADE,
        related_name='attendance_sessions',
    )
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    check_in_at = models.DateTimeField()
    check_out_at = models.DateTimeField(null=True, blank=True)
    check_in_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    check_in_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    check_in_accuracy_m = models.FloatField(null=True, blank=True)
    check_out_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
    )
    check_out_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
    )
    check_out_accuracy_m = models.FloatField(null=True, blank=True)
    total_distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('0.00'),
    )

    class Meta:
        verbose_name = 'Attendance Session'
        verbose_name_plural = 'Attendance Sessions'
        indexes = [
            models.Index(fields=['date', 'profile']),
            models.Index(fields=['profile', '-check_in_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'date'],
                name='unique_attendance_per_profile_per_day',
            ),
        ]

    def __str__(self):
        return f'{self.profile.display_name} — {self.date}'


class LocationPing(BaseModel):
    """GPS location ping from mobile app during active attendance."""

    profile = models.ForeignKey(
        TrackingProfile,
        on_delete=models.CASCADE,
        related_name='location_pings',
    )
    attendance_session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pings',
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy_m = models.FloatField(null=True, blank=True)
    altitude_m = models.FloatField(null=True, blank=True)
    speed_mps = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    battery_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(db_index=True)
    is_moving = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Location Ping'
        verbose_name_plural = 'Location Pings'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['profile', '-recorded_at']),
            models.Index(fields=['attendance_session', 'recorded_at']),
        ]

    def __str__(self):
        return f'Ping {self.profile_id} @ {self.recorded_at}'
