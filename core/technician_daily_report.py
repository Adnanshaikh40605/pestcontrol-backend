"""
Technician type reports for CRM.

Product language maps "Priority" technicians to TechnicianType.PARTNER
(broadcast + 40/60 payout). Secondary and Salaried keep their API values.

Performance rule (CRM Technician Reports):
  A technician is **Performed** for the selected Asia/Kolkata date range if they
  have ≥1 booking with status **On Process** in that range as lead
  (JobCard.technician) or active crew (participation not absent).
  Cancelled / Done / other statuses are excluded.
  Active technicians of that type with zero matching On Process bookings are
  **Not Performed**.

Optional filters: city (job city / master city), from/to date range.
Earnings use the same technician share the ledger shows.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Prefetch, Q

from core.models import (
    JobCard,
    JobCardTechnicianParticipation,
    SettlementLineItem,
    Technician,
)
from partner.models import PartnerEarning

# Desk dates are always India, even if the CRM browser is elsewhere.
IST = ZoneInfo('Asia/Kolkata')

# CRM product labels — Priority == partner (broadcast pool).
TYPE_DISPLAY = {
    Technician.TechnicianType.PARTNER: 'Priority (Partner)',
    Technician.TechnicianType.SECONDARY: 'Secondary',
    Technician.TechnicianType.SALARIED: 'Salaried',
}

PERFORMING_RULE = (
    'at least one On Process booking in the selected Asia/Kolkata date range '
    '(lead technician or active crew). Cancelled, Done, and other statuses '
    'are excluded. Earnings are the ledger share of the stored service base.'
)

# Keep alias used by older CRM copy / tests.
PERFORMED_RULE = PERFORMING_RULE


def kolkata_today() -> date:
    return datetime.now(IST).date()


def _parse_report_date(raw: str | None) -> date:
    if not raw:
        return kolkata_today()
    try:
        return datetime.strptime(raw.strip()[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError('date must be YYYY-MM-DD')


def _parse_date_bound(raw: str | None, *, label: str) -> date | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        return datetime.strptime(str(raw).strip()[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError(f'{label} must be YYYY-MM-DD')


def _ist_day_bounds(report_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(report_date, time.min, tzinfo=IST)
    return start, start + timedelta(days=1)


def _ist_range_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from:
        raise ValueError('to must be on or after from')
    start = datetime.combine(date_from, time.min, tzinfo=IST)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=IST)
    return start, end


def _normalize_type(raw: str | None) -> str:
    value = (raw or Technician.TechnicianType.PARTNER).strip().lower()
    # Product alias used in CRM copy
    if value in ('priority', 'partner'):
        return Technician.TechnicianType.PARTNER
    if value == Technician.TechnicianType.SECONDARY:
        return Technician.TechnicianType.SECONDARY
    if value == Technician.TechnicianType.SALARIED:
        return Technician.TechnicianType.SALARIED
    raise ValueError(
        'technician_type must be partner|priority|secondary|salaried'
    )


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0.00')


def _job_city(job: JobCard) -> str:
    if job.master_city_id and getattr(job, 'master_city', None):
        name = (job.master_city.name or '').strip()
        if name:
            return name
    return (job.city or '').strip() or 'Unknown'


def _normalize_city_filter(raw: str | None) -> str | None:
    value = (raw or '').strip()
    return value or None


def _city_matches(job: JobCard, city_filter: str) -> bool:
    target = city_filter.strip().lower()
    if not target:
        return True
    job_city = _job_city(job).strip().lower()
    return job_city == target or target in job_city


def _service_labels(job: JobCard) -> list[str]:
    """One display name per service line on a visit."""
    from core.pricing.aliases import canonical_service_line, clean_service_label

    raws: list[str] = []
    items = job.service_items if isinstance(job.service_items, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        svc = (item.get('service') or item.get('service_type') or '').strip()
        if svc:
            raws.append(svc)
    if not raws:
        fallback = (job.service_type or '').strip()
        raws = [fallback] if fallback else ['Unknown']

    labels: list[str] = []
    for raw in raws:
        label = canonical_service_line(raw) or clean_service_label(raw) or 'Unknown'
        if label not in labels:
            labels.append(label)
    return labels


def _ledger_share(job: JobCard, technician: Technician) -> Decimal:
    """
    Technician share for the report row.

    Ledger payouts are finalized on Done visits. For On Process bookings we
    project the same stored snapshot (participation / visit_payout) so city
    earnings still reflect the assigned share without inventing new rules.
    """
    if technician.technician_type == Technician.TechnicianType.SALARIED:
        return Decimal('0.00')

    if job.status == JobCard.JobStatus.DONE:
        from core.technician_ledger import serialize_ledger_row

        return _money(serialize_ledger_row(job, technician).get('technician_share'))

    participation = next(
        (
            row
            for row in job.technician_participations.all()
            if row.technician_id == technician.id
        ),
        None,
    )
    if participation is not None and participation.payout_amount_snapshot:
        snap = _money(participation.payout_amount_snapshot)
        if snap > 0:
            return snap

    if job.technician_id == technician.id and job.visit_payout_amount:
        return _money(job.visit_payout_amount)

    return Decimal('0.00')


def _with_ledger_relations(qs):
    return qs.select_related(
        'technician', 'master_city', 'client', 'parent_job',
    ).prefetch_related(
        Prefetch(
            'technician_participations',
            queryset=JobCardTechnicianParticipation.objects.select_related(
                'technician', 'partner',
            ),
        ),
        Prefetch(
            'partner_earnings',
            queryset=PartnerEarning.objects.select_related('partner'),
        ),
        Prefetch(
            'settlement_line_items',
            queryset=SettlementLineItem.objects.select_related('settlement'),
        ),
        'feedbacks',
    )


def _package_shell_ids(jobs_by_id: dict[int, JobCard]) -> set[int]:
    """Multi-service package shells are not visits; their day-1 children are."""
    if not jobs_by_id:
        return set()
    from core.booking_schedule_engine import service_line_names

    parents = set(
        JobCard.objects.filter(
            parent_job_id__in=list(jobs_by_id.keys()),
            service_cycle=1,
        ).values_list('parent_job_id', flat=True)
    )
    shells: set[int] = set()
    for job_id in parents:
        job = jobs_by_id.get(job_id)
        if job is not None and len(service_line_names(job)) > 1:
            shells.add(job_id)
    return shells


def _resolve_report_window(
    *,
    report_date: date | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date, datetime, datetime]:
    """
    Resolve Asia/Kolkata inclusive date window.

    Prefer from/to when provided; otherwise use single `date` (default today).
    """
    if date_from is not None or date_to is not None:
        start_day = date_from or date_to or kolkata_today()
        end_day = date_to or date_from or start_day
        start, end = _ist_range_bounds(start_day, end_day)
        return start_day, end_day, start, end

    day = report_date or kolkata_today()
    start, end = _ist_day_bounds(day)
    return day, day, start, end


def build_daily_type_report(
    *,
    report_date: date | None = None,
    technician_type: str,
    date_from: date | None = None,
    date_to: date | None = None,
    city: str | None = None,
) -> dict[str, Any]:
    start_day, end_day, start, end = _resolve_report_window(
        report_date=report_date,
        date_from=date_from,
        date_to=date_to,
    )
    city_filter = _normalize_city_filter(city)

    techs = list(
        Technician.objects.filter(
            is_active=True,
            technician_type=technician_type,
        ).select_related('partner_account').order_by('name')
    )
    tech_ids = [t.id for t in techs]
    tech_by_id = {t.id: t for t in techs}

    # Process bookings only — schedule date in the selected IST window.
    schedule_in_range = Q(
        schedule_datetime__gte=start,
        schedule_datetime__lt=end,
    )
    process_status = JobCard.JobStatus.ON_PROCESS

    lead_qs = JobCard.objects.filter(
        status=process_status,
        technician_id__in=tech_ids,
    ).filter(schedule_in_range)
    if city_filter:
        lead_qs = lead_qs.filter(
            Q(master_city__name__iexact=city_filter)
            | Q(city__iexact=city_filter)
            | Q(master_city__name__icontains=city_filter)
            | Q(city__icontains=city_filter)
        )

    lead_jobs = list(_with_ledger_relations(lead_qs)) if tech_ids else []

    # Active crew on On Process jobs (exclude absent).
    active_attendance = [
        JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED,
        JobCardTechnicianParticipation.AttendanceStatus.CHECKED_IN,
        JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
    ]
    part_qs = JobCardTechnicianParticipation.objects.filter(
        technician_id__in=tech_ids,
        jobcard__status=process_status,
        attendance_status__in=active_attendance,
        jobcard__schedule_datetime__gte=start,
        jobcard__schedule_datetime__lt=end,
    )
    if city_filter:
        part_qs = part_qs.filter(
            Q(jobcard__master_city__name__iexact=city_filter)
            | Q(jobcard__city__iexact=city_filter)
            | Q(jobcard__master_city__name__icontains=city_filter)
            | Q(jobcard__city__icontains=city_filter)
        )

    participations = list(
        part_qs.select_related('technician')
    ) if tech_ids else []

    crew_job_ids = {
        part.jobcard_id
        for part in participations
        if part.jobcard_id not in {job.id for job in lead_jobs}
    }
    crew_jobs = list(
        _with_ledger_relations(
            JobCard.objects.filter(id__in=crew_job_ids)
        )
    ) if crew_job_ids else []

    jobs_by_id: dict[int, JobCard] = {job.id: job for job in lead_jobs}
    for job in crew_jobs:
        jobs_by_id[job.id] = job
    shells = _package_shell_ids(jobs_by_id)

    completed_job_ids: dict[int, set[int]] = defaultdict(set)
    service_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    city_earnings: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    city_jobs: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_earnings: dict[int, Decimal] = defaultdict(lambda: Decimal('0.00'))

    def _credit(job: JobCard, technician_id: int) -> None:
        if job.id in shells or technician_id not in tech_by_id:
            return
        if city_filter and not _city_matches(job, city_filter):
            return
        if job.id in completed_job_ids[technician_id]:
            return
        completed_job_ids[technician_id].add(job.id)
        for label in _service_labels(job):
            service_counts[technician_id][label] += 1
        job_city = _job_city(job)
        payout = _ledger_share(job, tech_by_id[technician_id])
        city_earnings[technician_id][job_city] += payout
        city_jobs[technician_id][job_city] += 1
        total_earnings[technician_id] += payout

    for job in lead_jobs:
        if job.technician_id:
            _credit(job, job.technician_id)

    for part in participations:
        job = jobs_by_id.get(part.jobcard_id)
        if job is None:
            continue
        _credit(job, part.technician_id)

    def row_for(tech: Technician) -> dict[str, Any]:
        services = [
            {'service_type': svc, 'count': count}
            for svc, count in sorted(
                service_counts[tech.id].items(),
                key=lambda x: (-x[1], x[0]),
            )
        ]
        cities = [
            {
                'city': cname,
                'completed_jobs': city_jobs[tech.id][cname],
                'process_jobs': city_jobs[tech.id][cname],
                'earnings': str(city_earnings[tech.id][cname]),
            }
            for cname in sorted(city_earnings[tech.id].keys())
        ]
        primary_city = (
            (tech.city or '').strip()
            or (cities[0]['city'] if cities else '')
            or (tech.service_area or '').strip()
            or '—'
        )
        process_count = len(completed_job_ids[tech.id])
        status = 'Performed' if process_count >= 1 else 'Not Performed'
        return {
            'id': tech.id,
            'name': tech.name,
            'mobile': tech.mobile,
            'technician_type': tech.technician_type,
            'city': primary_city,
            'completed_count': process_count,
            'process_count': process_count,
            'performance_status': status,
            'services': services,
            'services_summary': ', '.join(
                f'{s["service_type"]} {s["count"]}' for s in services
            )
            or '—',
            'earnings': str(total_earnings[tech.id]),
            'city_earnings': cities,
        }

    performing = []
    non_performing = []
    all_rows: list[dict[str, Any]] = []
    for tech in techs:
        row = row_for(tech)
        all_rows.append(row)
        if row['process_count'] >= 1:
            performing.append(row)
        else:
            non_performing.append(row)

    rollup: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            'city': '',
            'completed_jobs': 0,
            'earnings': Decimal('0.00'),
            'technician_ids': set(),
        }
    )
    for row in all_rows:
        for city_row in row['city_earnings']:
            cname = city_row['city']
            bucket = rollup[cname]
            bucket['city'] = cname
            bucket['completed_jobs'] += city_row['completed_jobs']
            bucket['earnings'] += _money(city_row['earnings'])
            if city_row['completed_jobs'] > 0:
                bucket['technician_ids'].add(row['id'])

    city_earnings_list = [
        {
            'city': data['city'],
            'completed_jobs': data['completed_jobs'],
            'process_jobs': data['completed_jobs'],
            'earnings': str(data['earnings']),
            'technician_count': len(data['technician_ids']),
        }
        for data in sorted(
            rollup.values(),
            key=lambda d: (-d['earnings'], d['city']),
        )
    ]

    performing_earnings = sum((_money(r['earnings']) for r in performing), Decimal('0.00'))
    return {
        'date': start_day.isoformat() if start_day == end_day else None,
        'from': start_day.isoformat(),
        'to': end_day.isoformat(),
        'city': city_filter,
        'booking_status': process_status,
        'technician_type': technician_type,
        'technician_type_label': TYPE_DISPLAY.get(technician_type, technician_type),
        'performing_rule': PERFORMING_RULE,
        'performance_rule': PERFORMED_RULE,
        'summary': {
            'total_technicians': len(techs),
            'performing_count': len(performing),
            'non_performing_count': len(non_performing),
            'performed_count': len(performing),
            'not_performed_count': len(non_performing),
            'total_completed_jobs': sum(r['process_count'] for r in performing),
            'total_process_jobs': sum(r['process_count'] for r in performing),
            'total_earnings': str(performing_earnings),
        },
        # Legacy keys kept for existing CRM; UI labels say Performed / Not Performed.
        'performing': performing,
        'non_performing': non_performing,
        'performed': performing,
        'not_performed': non_performing,
        'city_earnings': city_earnings_list,
    }
