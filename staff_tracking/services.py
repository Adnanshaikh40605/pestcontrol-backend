"""Business logic for staff tracking."""

from __future__ import annotations

import math
from datetime import date, datetime, time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import Technician

from .identity import get_or_create_profile, resolve_profile_from_partner
from .models import AttendanceSession, LocationPing, TrackingProfile, TrackingSettings


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two GPS points in kilometres."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_active_session(profile: TrackingProfile, for_date: date | None = None) -> AttendanceSession | None:
    target = for_date or timezone.localdate()
    return (
        AttendanceSession.objects.filter(
            profile=profile,
            date=target,
            status=AttendanceSession.Status.ACTIVE,
        )
        .order_by('-check_in_at')
        .first()
    )


def is_late_checkin(check_in_at: datetime) -> bool:
    settings = TrackingSettings.get_solo()
    local = timezone.localtime(check_in_at)
    shift_start = datetime.combine(local.date(), settings.shift_start_time)
    shift_start = timezone.make_aware(shift_start, timezone.get_current_timezone())
    grace = timezone.timedelta(minutes=settings.grace_minutes)
    return local > shift_start + grace


@transaction.atomic
def check_in(
    profile: TrackingProfile,
    *,
    latitude: float,
    longitude: float,
    accuracy_m: float | None = None,
    ip_address: str | None = None,
) -> AttendanceSession:
    from .identity import ensure_consent

    ensure_consent(profile, ip_address=ip_address)

    today = timezone.localdate()
    existing = get_active_session(profile, today)
    if existing:
        return existing

    now = timezone.now()
    session = AttendanceSession.objects.create(
        profile=profile,
        date=today,
        status=AttendanceSession.Status.ACTIVE,
        check_in_at=now,
        check_in_latitude=latitude,
        check_in_longitude=longitude,
        check_in_accuracy_m=accuracy_m,
    )

    profile.technician.last_active = now
    profile.technician.save(update_fields=['last_active', 'updated_at'])

    return session


@transaction.atomic
def check_out(
    profile: TrackingProfile,
    *,
    latitude: float,
    longitude: float,
    accuracy_m: float | None = None,
) -> AttendanceSession:
    session = get_active_session(profile)
    if session is None:
        raise ValueError('No active check-in session found.')

    now = timezone.now()
    session.check_out_at = now
    session.check_out_latitude = latitude
    session.check_out_longitude = longitude
    session.check_out_accuracy_m = accuracy_m
    session.status = AttendanceSession.Status.COMPLETED
    session.total_distance_km = compute_session_distance(session)
    session.save()

    profile.technician.last_active = now
    profile.technician.save(update_fields=['last_active', 'updated_at'])
    return session


def compute_session_distance(session: AttendanceSession) -> Decimal:
    pings = list(
        session.pings.order_by('recorded_at').values_list('latitude', 'longitude')
    )
    if len(pings) < 2:
        return Decimal('0.00')

    total = 0.0
    for i in range(1, len(pings)):
        lat1, lon1 = float(pings[i - 1][0]), float(pings[i - 1][1])
        lat2, lon2 = float(pings[i][0]), float(pings[i][1])
        total += haversine_km(lat1, lon1, lat2, lon2)
    return Decimal(str(round(total, 2)))


@transaction.atomic
def record_ping(
    profile: TrackingProfile,
    *,
    latitude: float,
    longitude: float,
    recorded_at: datetime | None = None,
    accuracy_m: float | None = None,
    altitude_m: float | None = None,
    speed_mps: float | None = None,
    heading: float | None = None,
    battery_percent: int | None = None,
    is_moving: bool = True,
) -> LocationPing:
    session = get_active_session(profile)
    if session is None:
        raise ValueError('GPS tracking is only allowed during an active check-in session.')

    when = recorded_at or timezone.now()
    ping = LocationPing.objects.create(
        profile=profile,
        attendance_session=session,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        altitude_m=altitude_m,
        speed_mps=speed_mps,
        heading=heading,
        battery_percent=battery_percent,
        recorded_at=when,
        is_moving=is_moving,
    )

    profile.technician.last_active = when
    profile.technician.save(update_fields=['last_active', 'updated_at'])
    return ping


def record_ping_batch(profile: TrackingProfile, pings: list[dict]) -> int:
    created = 0
    for item in pings:
        try:
            record_ping(profile, **item)
            created += 1
        except ValueError:
            continue
    return created


def get_last_ping(profile: TrackingProfile) -> LocationPing | None:
    return profile.location_pings.order_by('-recorded_at').first()


def staff_live_status(profile: TrackingProfile) -> str:
    session = get_active_session(profile)
    if session:
        last = get_last_ping(profile)
        if last and last.recorded_at >= timezone.now() - timezone.timedelta(minutes=10):
            return 'on_duty'
        return 'checked_in_idle'
    return 'off_duty'


def backfill_profiles_for_technicians() -> int:
    """Create tracking profiles for all active technicians."""
    count = 0
    for tech in Technician.objects.filter(is_active=True):
        partner = getattr(tech, 'partner_account', None)
        get_or_create_profile(tech, partner=partner)
        count += 1
    return count
