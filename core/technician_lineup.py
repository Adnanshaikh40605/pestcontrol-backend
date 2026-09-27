"""Same-day schedule and booking-family assignments for the CRM assign popup.

Uses the existing JobCard.technician lead and JobCardTechnicianParticipation
crew rows. It does not create another assignment record.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Prefetch, Q
from django.utils import timezone

from core.models import JobCard, JobCardTechnicianParticipation

OPEN_LINEUP_STATUSES = (
    JobCard.JobStatus.UPCOMING,
    JobCard.JobStatus.PENDING,
    JobCard.JobStatus.ON_PROCESS,
)

ACTIVE_ATTENDANCE = (
    JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED,
    JobCardTechnicianParticipation.AttendanceStatus.CHECKED_IN,
    JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
)

MAX_LINEUP_BOOKINGS = 12


def build_assign_lineup_context(technicians, job: JobCard | None = None) -> dict:
    """Maps for TechnicianSerializer: lineup_bookings and assigned_service_lines."""
    tech_ids = [tech.id for tech in technicians]
    lineup: dict[int, list] = {tech_id: [] for tech_id in tech_ids}
    assigned: dict[int, list] = {tech_id: [] for tech_id in tech_ids}
    if not tech_ids:
        return {'lineup_bookings': lineup, 'assigned_service_lines': assigned}

    family_ids = _booking_family_ids(job)
    if family_ids:
        family_jobs = _jobs_with_crew(
            JobCard.objects.filter(id__in=family_ids),
            tech_ids,
        )
        for row in family_jobs:
            _attach(assigned, row, tech_ids, this_booking=True, limit=MAX_LINEUP_BOOKINGS)

    anchor = job.schedule_datetime if job is not None and job.schedule_datetime else timezone.now()
    start, end = _local_day_bounds(anchor)
    day_jobs = _jobs_with_crew(
        JobCard.objects.filter(status__in=OPEN_LINEUP_STATUSES)
        .filter(schedule_datetime__gte=start, schedule_datetime__lt=end)
        .filter(
            Q(technician_id__in=tech_ids)
            | Q(
                technician_participations__technician_id__in=tech_ids,
                technician_participations__attendance_status__in=ACTIVE_ATTENDANCE,
            )
        )
        .distinct()
        .order_by('schedule_datetime', 'id'),
        tech_ids,
    )
    for row in day_jobs:
        _attach(
            lineup,
            row,
            tech_ids,
            this_booking=row.id in family_ids,
            limit=MAX_LINEUP_BOOKINGS,
        )

    return {'lineup_bookings': lineup, 'assigned_service_lines': assigned}


def _booking_family_ids(job: JobCard | None) -> set[int]:
    """This booking plus its service-line / follow-up children, excluding cancelled."""
    if job is None:
        return set()
    root_id = job.parent_job_id or job.id
    return set(
        JobCard.objects.filter(Q(id=root_id) | Q(parent_job_id=root_id))
        .exclude(status=JobCard.JobStatus.CANCELLED)
        .values_list('id', flat=True)
    )


def _local_day_bounds(moment):
    local = timezone.localtime(moment)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _jobs_with_crew(qs, tech_ids):
    return qs.select_related(
        'client', 'master_city', 'master_location', 'technician',
    ).prefetch_related(
        Prefetch(
            'technician_participations',
            queryset=JobCardTechnicianParticipation.objects.filter(
                technician_id__in=tech_ids,
                attendance_status__in=ACTIVE_ATTENDANCE,
            ),
        )
    )


def _attach(bucket, job, tech_ids, *, this_booking: bool, limit: int) -> None:
    for tech_id, role in _techs_on_job(job, tech_ids):
        rows = bucket.setdefault(tech_id, [])
        if any(row['id'] == job.id for row in rows):
            continue
        if len(rows) >= limit:
            continue
        rows.append(_payload(job, role, this_booking))


def _techs_on_job(job, tech_ids) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    seen: set[int] = set()
    if job.technician_id in tech_ids:
        found.append((job.technician_id, 'lead'))
        seen.add(job.technician_id)
    for part in job.technician_participations.all():
        if part.attendance_status == JobCardTechnicianParticipation.AttendanceStatus.ABSENT:
            continue
        if part.technician_id not in tech_ids or part.technician_id in seen:
            continue
        role = (
            'lead'
            if part.role == JobCardTechnicianParticipation.Role.LEAD
            else 'crew'
        )
        found.append((part.technician_id, role))
        seen.add(part.technician_id)
    return found


def _payload(job, role: str, this_booking: bool) -> dict:
    city = ''
    if job.master_city_id and getattr(job, 'master_city', None):
        city = (job.master_city.name or '').strip()
    if not city:
        city = (job.city or '').strip()
    location = ''
    if job.master_location_id and getattr(job, 'master_location', None):
        location = (job.master_location.name or '').strip()
    client = getattr(job, 'client', None)
    client_name = (client.full_name or '').strip() if client is not None else ''
    return {
        'id': job.id,
        'client_name': client_name,
        'service_type': (job.source_service or job.service_type or '').strip(),
        'status': job.status,
        'schedule_datetime': job.schedule_datetime.isoformat() if job.schedule_datetime else None,
        'time_slot': job.time_slot or '',
        'city': city,
        'location': location,
        'role': role,
        'this_booking': bool(this_booking),
    }
