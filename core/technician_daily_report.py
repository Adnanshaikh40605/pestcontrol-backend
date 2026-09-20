"""
Daily technician type reports for CRM.

Product language maps "Priority" technicians to TechnicianType.PARTNER
(broadcast + 40/60 payout). Secondary and Salaried keep their API values.

Performing rule (documented for CRM UI):
  A technician is **performing** for a given calendar day if they completed
  ≥1 Done job that day as lead (JobCard.technician) or crew
  (JobCardTechnicianParticipation with COMPLETED / DONE attendance).
  Otherwise active technicians of that type are **non-performing**.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils import timezone

from core.models import JobCard, JobCardTechnicianParticipation, Technician
from core.pricing.gst import amount_excluding_gst, resolve_job_gst_percent

# CRM product labels — Priority == partner (broadcast pool).
TYPE_DISPLAY = {
    Technician.TechnicianType.PARTNER: 'Priority (Partner)',
    Technician.TechnicianType.SECONDARY: 'Secondary',
    Technician.TechnicianType.SALARIED: 'Salaried',
}

PERFORMING_RULE = (
    'completed ≥ 1 Done job on the selected date '
    '(as lead technician or completed crew participation)'
)


def _parse_report_date(raw: str | None) -> date:
    if not raw:
        return timezone.localdate()
    try:
        return datetime.strptime(raw.strip()[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError('date must be YYYY-MM-DD')


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


def _job_service_label(job: JobCard) -> str:
    items = job.service_items if isinstance(job.service_items, list) else []
    labels: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        svc = (item.get('service') or item.get('service_type') or '').strip()
        if svc and svc not in labels:
            labels.append(svc)
    if labels:
        return ', '.join(labels)
    return (job.service_type or 'Unknown').strip() or 'Unknown'


def _payout_for_tech(job: JobCard, technician_id: int, participation_map: dict) -> Decimal:
    """Prefer immutable participation snapshot; fall back to lead visit payout."""
    part = participation_map.get((job.id, technician_id))
    if part is not None and part.payout_amount_snapshot is not None:
        snap = _money(part.payout_amount_snapshot)
        if snap > 0:
            return amount_excluding_gst(snap, resolve_job_gst_percent(job))

    tech = getattr(job, 'technician', None)
    if tech is not None and tech.id == technician_id:
        if getattr(tech, 'technician_type', None) == Technician.TechnicianType.SALARIED:
            return Decimal('0.00')
        raw = job.visit_payout_amount
        if raw is not None and _money(raw) > 0:
            return amount_excluding_gst(raw, resolve_job_gst_percent(job))
        # Legacy: 40% of excl-GST price when snapshots missing
        price = _money(job.price or job.total_amount or 0)
        if price > 0:
            base = amount_excluding_gst(price, resolve_job_gst_percent(job))
            return (base * Decimal('0.40')).quantize(Decimal('0.01'))
    return Decimal('0.00')


def build_daily_type_report(*, report_date: date, technician_type: str) -> dict[str, Any]:
    techs = list(
        Technician.objects.filter(
            is_active=True,
            technician_type=technician_type,
        ).order_by('name')
    )
    tech_ids = [t.id for t in techs]
    tech_by_id = {t.id: t for t in techs}

    # Done jobs on this calendar day where tech is lead.
    lead_jobs = list(
        JobCard.objects.filter(
            status=JobCard.JobStatus.DONE,
            technician_id__in=tech_ids,
        )
        .filter(
            Q(completed_at__date=report_date)
            | Q(completed_at__isnull=True, schedule_datetime__date=report_date)
        )
        .select_related('technician', 'master_city')
    )

    # Crew completions on this day (completed attendance only — not absent/assigned).
    participation_qs = (
        JobCardTechnicianParticipation.objects.filter(
            technician_id__in=tech_ids,
            jobcard__status=JobCard.JobStatus.DONE,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
        )
        .filter(
            Q(jobcard__completed_at__date=report_date)
            | Q(
                jobcard__completed_at__isnull=True,
                jobcard__schedule_datetime__date=report_date,
            )
        )
        .select_related('jobcard', 'jobcard__master_city', 'technician')
    )
    participations = list(participation_qs)
    participation_map = {(p.jobcard_id, p.technician_id): p for p in participations}

    # Aggregate per technician
    completed_job_ids: dict[int, set[int]] = defaultdict(set)
    service_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    city_earnings: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    city_jobs: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_earnings: dict[int, Decimal] = defaultdict(lambda: Decimal('0.00'))

    jobs_by_id: dict[int, JobCard] = {}
    for job in lead_jobs:
        jobs_by_id[job.id] = job
        tid = job.technician_id
        if tid not in tech_by_id:
            continue
        completed_job_ids[tid].add(job.id)
        label = _job_service_label(job)
        service_counts[tid][label] += 1
        city = _job_city(job)
        payout = _payout_for_tech(job, tid, participation_map)
        city_earnings[tid][city] += payout
        city_jobs[tid][city] += 1
        total_earnings[tid] += payout

    for part in participations:
        job = part.jobcard
        jobs_by_id[job.id] = job
        tid = part.technician_id
        if tid not in tech_by_id:
            continue
        if job.id in completed_job_ids[tid]:
            # Already counted as lead — avoid double-counting services/jobs
            continue
        completed_job_ids[tid].add(job.id)
        label = _job_service_label(job)
        service_counts[tid][label] += 1
        city = _job_city(job)
        payout = _payout_for_tech(job, tid, participation_map)
        city_earnings[tid][city] += payout
        city_jobs[tid][city] += 1
        total_earnings[tid] += payout

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
                f'{s["service_type"]} ×{s["count"]}' for s in services
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

    # City-wise rollup across all technicians of this type for the day
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
