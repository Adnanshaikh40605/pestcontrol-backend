"""Business logic for visits, tasks, leave, and expenses."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import JobCard

from .models import AttendanceBreak, AttendanceSession, TrackingProfile, TrackingSettings
from .operations_models import (
    ExpenseCategory,
    ExpenseClaim,
    FieldVisit,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    StaffTask,
)
from .services import get_active_session, haversine_km, is_late_checkin


def within_radius_m(
    lat1: float, lon1: float, lat2: float, lon2: float, radius_m: float,
) -> tuple[bool, float]:
    distance_km = haversine_km(lat1, lon1, lat2, lon2)
    distance_m = distance_km * 1000
    return distance_m <= radius_m, distance_m


@transaction.atomic
def visit_check_in(
    visit: FieldVisit,
    *,
    latitude: float,
    longitude: float,
    accuracy_m: float | None = None,
) -> FieldVisit:
    settings = TrackingSettings.get_solo()
    if visit.status not in {FieldVisit.Status.SCHEDULED, FieldVisit.Status.IN_PROGRESS}:
        raise ValueError('Visit is not available for check-in.')

    if visit.latitude is not None and visit.longitude is not None:
        ok, distance_m = within_radius_m(
            latitude,
            longitude,
            float(visit.latitude),
            float(visit.longitude),
            settings.visit_checkin_radius_m,
        )
        if not ok:
            raise ValueError(
                f'You must be within {settings.visit_checkin_radius_m}m of the visit location '
                f'(currently {distance_m:.0f}m away).',
            )

    now = timezone.now()
    visit.check_in_at = now
    visit.check_in_latitude = latitude
    visit.check_in_longitude = longitude
    visit.check_in_accuracy_m = accuracy_m
    visit.status = FieldVisit.Status.IN_PROGRESS
    visit.save()
    return visit


@transaction.atomic
def visit_check_out(
    visit: FieldVisit,
    *,
    latitude: float,
    longitude: float,
    notes: str = '',
) -> FieldVisit:
    if visit.status != FieldVisit.Status.IN_PROGRESS:
        raise ValueError('Visit is not in progress.')

    now = timezone.now()
    visit.check_out_at = now
    visit.check_out_latitude = latitude
    visit.check_out_longitude = longitude
    if notes:
        visit.notes = notes
    visit.status = FieldVisit.Status.COMPLETED
    visit.save()
    return visit


def sync_jobcards_to_visits(profile: TrackingProfile, for_date: date | None = None) -> int:
    """Create FieldVisit rows from today's JobCards assigned to this technician."""
    target = for_date or timezone.localdate()
    tech = profile.technician
    jobcards = JobCard.objects.filter(
        technician=tech,
        schedule_datetime__date=target,
        status__in=['Upcoming', 'Pending', 'On Process'],
    ).exclude(field_visits__scheduled_at__date=target)

    created = 0
    for jc in jobcards:
        if FieldVisit.objects.filter(profile=profile, jobcard=jc, scheduled_at__date=target).exists():
            continue
        scheduled_at = jc.schedule_datetime or timezone.make_aware(datetime.combine(target, time(9, 0)))
        FieldVisit.objects.create(
            profile=profile,
            jobcard=jc,
            title=f'{jc.booking_type} — {jc.code}',
            client_name=jc.client.name if jc.client_id else '',
            address=jc.client_address or jc.full_address or '',
            scheduled_at=scheduled_at,
            status=FieldVisit.Status.SCHEDULED,
        )
        created += 1
    return created


@transaction.atomic
def start_break(profile: TrackingProfile, *, latitude: float | None = None, longitude: float | None = None) -> AttendanceBreak:
    session = get_active_session(profile)
    if session is None:
        raise ValueError('Check in before starting a break.')

    active = session.breaks.filter(ended_at__isnull=True).first()
    if active:
        return active

    return AttendanceBreak.objects.create(
        session=session,
        started_at=timezone.now(),
        latitude=latitude,
        longitude=longitude,
    )


@transaction.atomic
def end_break(profile: TrackingProfile) -> AttendanceBreak:
    session = get_active_session(profile)
    if session is None:
        raise ValueError('No active session.')

    brk = session.breaks.filter(ended_at__isnull=True).first()
    if brk is None:
        raise ValueError('No active break.')

    brk.ended_at = timezone.now()
    brk.save(update_fields=['ended_at', 'updated_at'])
    return brk


def compute_working_minutes(session: AttendanceSession) -> int:
    if not session.check_out_at:
        return 0

    total = (session.check_out_at - session.check_in_at).total_seconds() / 60
    for brk in session.breaks.filter(ended_at__isnull=False):
        total -= (brk.ended_at - brk.started_at).total_seconds() / 60
    return max(0, int(total))


@transaction.atomic
def finalize_attendance(session: AttendanceSession) -> AttendanceSession:
    """Compute working minutes and attendance result after checkout."""
    settings = TrackingSettings.get_solo()
    session.working_minutes = compute_working_minutes(session)
    session.is_late = is_late_checkin(session.check_in_at)

    if session.is_late:
        session.attendance_result = AttendanceSession.AttendanceResult.LATE
    else:
        session.attendance_result = AttendanceSession.AttendanceResult.PRESENT

    if session.check_out_at:
        local_out = timezone.localtime(session.check_out_at)
        shift_end = timezone.datetime.combine(local_out.date(), settings.shift_end_time)
        shift_end = timezone.make_aware(shift_end, timezone.get_current_timezone())
        if local_out < shift_end - timezone.timedelta(minutes=settings.grace_minutes):
            session.attendance_result = AttendanceSession.AttendanceResult.EARLY_DEPARTURE

    session.save()
    return session


@transaction.atomic
def apply_leave(
    profile: TrackingProfile,
    *,
    leave_type: LeaveType,
    start_date: date,
    end_date: date,
    reason: str,
    half_day: str = LeaveApplication.HalfDay.FULL,
) -> LeaveApplication:
    if end_date < start_date:
        raise ValueError('End date must be on or after start date.')

    days = (end_date - start_date).days + 1
    if half_day != LeaveApplication.HalfDay.FULL:
        days = Decimal('0.5')
    else:
        days = Decimal(str(days))

    app = LeaveApplication.objects.create(
        profile=profile,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        reason=reason,
        days_count=days,
    )

    balance, _ = LeaveBalance.objects.get_or_create(
        profile=profile,
        leave_type=leave_type,
        year=start_date.year,
        defaults={'allocated': leave_type.default_days_per_year},
    )
    balance.pending += days
    balance.save(update_fields=['pending', 'updated_at'])
    return app


@transaction.atomic
def review_leave(application: LeaveApplication, *, approved: bool, reviewer, comment: str = '') -> LeaveApplication:
    if application.status != LeaveApplication.Status.PENDING:
        raise ValueError('Leave application already reviewed.')

    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.reviewer_comment = comment
    application.status = (
        LeaveApplication.Status.APPROVED if approved else LeaveApplication.Status.REJECTED
    )
    application.save()

    balance = LeaveBalance.objects.filter(
        profile=application.profile,
        leave_type=application.leave_type,
        year=application.start_date.year,
    ).first()
    if balance:
        balance.pending = max(Decimal('0'), balance.pending - application.days_count)
        if approved:
            balance.used += application.days_count
        balance.save(update_fields=['pending', 'used', 'updated_at'])

    return application


@transaction.atomic
def submit_expense(
    profile: TrackingProfile,
    *,
    category: ExpenseCategory,
    expense_date: date,
    amount: Decimal,
    description: str = '',
    distance_km: Decimal | None = None,
    session: AttendanceSession | None = None,
) -> ExpenseClaim:
    if distance_km and category.km_rate:
        amount = Decimal(str(round(float(distance_km) * float(category.km_rate), 2)))

    return ExpenseClaim.objects.create(
        profile=profile,
        category=category,
        expense_date=expense_date,
        amount=amount,
        description=description,
        distance_km=distance_km,
        attendance_session=session,
        status=ExpenseClaim.Status.PENDING,
    )


@transaction.atomic
def review_expense(claim: ExpenseClaim, *, approved: bool, reviewer, comment: str = '') -> ExpenseClaim:
    if claim.status not in {ExpenseClaim.Status.PENDING, ExpenseClaim.Status.DRAFT}:
        raise ValueError('Expense claim already reviewed.')

    claim.reviewed_by = reviewer
    claim.reviewed_at = timezone.now()
    claim.reviewer_comment = comment
    claim.status = ExpenseClaim.Status.APPROVED if approved else ExpenseClaim.Status.REJECTED
    claim.save()
    return claim


@transaction.atomic
def update_task_status(
    task: StaffTask,
    *,
    new_status: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> StaffTask:
    if task.requires_gps_proof and new_status == StaffTask.Status.COMPLETED:
        if latitude is None or longitude is None:
            raise ValueError('GPS proof required to complete this task.')
        task.completion_latitude = latitude
        task.completion_longitude = longitude

    task.status = new_status
    if new_status == StaffTask.Status.COMPLETED:
        task.completed_at = timezone.now()
    task.save()
    return task
