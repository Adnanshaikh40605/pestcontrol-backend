"""
Daily technician type reports for CRM.

Product language maps "Priority" technicians to TechnicianType.PARTNER
(broadcast + 40/60 payout). Secondary and Salaried keep their API values.

Performing rule (documented for CRM UI):
  A technician is **performing** for a given Asia/Kolkata calendar day if they
  completed ≥1 Done job that day as lead (JobCard.technician) or crew
  (JobCardTechnicianParticipation with COMPLETED attendance).
  Cancelled jobs never count. Active technicians of that type with zero
  completed jobs are **non-performing**.

Earnings use the same technician share the ledger shows: the stored payout
(usually 40% of the stored service base, or another split when the record
stores one), scaled onto that base. An already ex-GST base is not divided
by 18% again.
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
    'completed at least one Done visit on this Asia/Kolkata date '
    '(lead technician or completed crew). Cancelled visits are ignored. '
    'Earnings are the ledger share of the stored service base.'
)


def kolkata_today() -> date:
    return datetime.now(IST).date()


def _parse_report_date(raw: str | None) -> date:
    if not raw:
        return kolkata_today()
    try:
        return datetime.strptime(raw.strip()[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError('date must be YYYY-MM-DD')


def _ist_day_bounds(report_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(report_date, time.min, tzinfo=IST)
    return start, start + timedelta(days=1)


def _done_on_day(start: datetime, end: datetime, *, prefix: str = '') -> Q:
    completed = f'{prefix}completed_at'
    schedule = f'{prefix}schedule_datetime'
    return Q(**{f'{completed}__gte': start, f'{completed}__lt': end}) | Q(
        **{
            f'{completed}__isnull': True,
            f'{schedule}__gte': start,
            f'{schedule}__lt': end,
        }
    )


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


def _service_labels(job: JobCard) -> list[str]:
    """One display name per service line on a completed visit.

    Legacy Cockroach / Ants labels show as Cockroach Standard so the desk
    sees the same names as Assign Technician.
    """
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
    """Same technician share the ledger row shows for this visit."""
    from core.technician_ledger import serialize_ledger_row

    row = serialize_ledger_row(job, technician)
    return _money(row.get('technician_share'))


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


def build_daily_type_report(*, report_date: date, technician_type: str) -> dict[str, Any]:
    techs = list(
        Technician.objects.filter(
            is_active=True,
            technician_type=technician_type,
        ).select_related('partner_account').order_by('name')
    )
    tech_ids = [t.id for t in techs]
    tech_by_id = {t.id: t for t in techs}
    start, end = _ist_day_bounds(report_date)
    on_day = _done_on_day(start, end)

    lead_jobs = list(
        _with_ledger_relations(
            JobCard.objects.filter(
                status=JobCard.JobStatus.DONE,
                technician_id__in=tech_ids,
            ).filter(on_day)
        )
    ) if tech_ids else []

    participations = list(
        JobCardTechnicianParticipation.objects.filter(
            technician_id__in=tech_ids,
            jobcard__status=JobCard.JobStatus.DONE,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
        ).filter(_done_on_day(start, end, prefix='jobcard__'))
        .select_related('technician')
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

    # technician -> completed job ids, then service / city rollups
    completed_job_ids: dict[int, set[int]] = defaultdict(set)
    service_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    city_earnings: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    city_jobs: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_earnings: dict[int, Decimal] = defaultdict(lambda: Decimal('0.00'))

    def _credit(job: JobCard, technician_id: int) -> None:
        if job.id in shells or technician_id not in tech_by_id:
            return
        if job.id in completed_job_ids[technician_id]:
            return
        completed_job_ids[technician_id].add(job.id)
        for label in _service_labels(job):
            service_counts[technician_id][label] += 1
        city = _job_city(job)
        payout = _ledger_share(job, tech_by_id[technician_id])
        city_earnings[technician_id][city] += payout
        city_jobs[technician_id][city] += 1
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
                'city': city,
                'completed_jobs': city_jobs[tech.id][city],
                'earnings': str(city_earnings[tech.id][city]),
            }
            for city in sorted(city_earnings[tech.id].keys())
        ]
        primary_city = (
            (tech.city or '').strip()
            or (cities[0]['city'] if cities else '')
            or (tech.service_area or '').strip()
            or '—'
        )
        return {
            'id': tech.id,
            'name': tech.name,
            'mobile': tech.mobile,
            'technician_type': tech.technician_type,
            'city': primary_city,
            'completed_count': len(completed_job_ids[tech.id]),
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
        if row['completed_count'] >= 1:
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
            city = city_row['city']
            bucket = rollup[city]
            bucket['city'] = city
            bucket['completed_jobs'] += city_row['completed_jobs']
            bucket['earnings'] += _money(city_row['earnings'])
            if city_row['completed_jobs'] > 0:
                bucket['technician_ids'].add(row['id'])

    city_earnings_list = [
        {
            'city': data['city'],
            'completed_jobs': data['completed_jobs'],
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
        'date': report_date.isoformat(),
        'technician_type': technician_type,
        'technician_type_label': TYPE_DISPLAY.get(technician_type, technician_type),
        'performing_rule': PERFORMING_RULE,
        'summary': {
            'total_technicians': len(techs),
            'performing_count': len(performing),
            'non_performing_count': len(non_performing),
            'total_completed_jobs': sum(r['completed_count'] for r in performing),
            'total_earnings': str(performing_earnings),
        },
        'performing': performing,
        'non_performing': non_performing,
        'city_earnings': city_earnings_list,
    }
