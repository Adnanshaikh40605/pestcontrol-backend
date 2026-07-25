"""
Configuration-driven visit scheduling for JobCard bookings.

Generates AMC / termite follow-up visits at booking creation time and
refreshes next-service dates when visits are completed.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Optional

from dateutil.relativedelta import relativedelta
from django.db.models import Q

logger = logging.getLogger(__name__)

# Months between visits for standard AMC packages.
AMC_INTERVAL_MONTHS: dict[int, int] = {
    3: 4,
    4: 3,
    6: 2,
    12: 1,
}

# High-frequency mosquito packages (days between visits).
MOSQUITO_INTERVAL_DAYS: dict[int, int] = {
    24: 15,
    48: 7,
}

# Society / quotation calendar frequencies → (unit, step).
# Visit count is derived from contract length (default 12 months).
CALENDAR_FREQUENCY_INTERVALS: dict[str, tuple[str, int]] = {
    'weekly': ('days', 7),
    'monthly': ('months', 1),
    'quarterly': ('months', 3),
    'half yearly': ('months', 6),
    'half-yearly': ('months', 6),
    'halfyearly': ('months', 6),
    'yearly': ('months', 12),
    'annually': ('months', 12),
    'annual': ('months', 12),
}

TERMITE_TOTAL_VISITS = 5
TERMITE_CHECKUP_INTERVAL_MONTHS = 6
DEFAULT_CONTRACT_MONTHS = 12
# Hard cap so Weekly over long contracts cannot explode the DB.
MAX_GENERATED_VISITS = 52


@dataclass(frozen=True)
class VisitPlan:
    cycle: int
    visit_date: date
    visit_type: str
    total_visits: int


@dataclass(frozen=True)
class RecurringSpec:
    """Resolved multi-visit schedule for a plan / frequency label."""

    visit_count: int
    unit: str  # 'days' | 'months'
    step: int
    label: str


def _normalize_plan_text(plan: str) -> str:
    return re.sub(r'\s+', ' ', (plan or '').strip().lower())


def parse_contract_months(contract_duration: Optional[str | int], default: int = DEFAULT_CONTRACT_MONTHS) -> int:
    try:
        months = int(str(contract_duration or '').strip() or default)
    except (TypeError, ValueError):
        months = default
    return max(1, min(months, 36))


def resolve_recurring_spec(
    plan: str,
    *,
    service: str = '',
    contract_months: Optional[int] = None,
    preferred_visit_count: Optional[int] = None,
) -> Optional[RecurringSpec]:
    """
    Parse AMC N Services / Society calendar frequencies into a recurring schedule.

    Supported plans (examples):
      - AMC 12 Services, 12 Services, AMC 6 Services, 3 Services, AMC
      - Weekly, Monthly, Quarterly, Half Yearly, Yearly
    """
    plan_l = _normalize_plan_text(plan)
    if not plan_l or 'one time' in plan_l:
        return None

    months = parse_contract_months(contract_months)

    # Explicit N-service packages (AMC 12 Services / 12 Services / etc.)
    match = re.search(r'(\d+)\s*service', plan_l)
    if match:
        visit_count = int(match.group(1))
        svc = (service or '').lower()
        if 'mosquito' in svc and visit_count in MOSQUITO_INTERVAL_DAYS:
            unit, step = 'days', MOSQUITO_INTERVAL_DAYS[visit_count]
        else:
            unit, step = 'months', AMC_INTERVAL_MONTHS.get(visit_count, 4)
        return RecurringSpec(
            visit_count=min(visit_count, MAX_GENERATED_VISITS),
            unit=unit,
            step=step,
            label=f'AMC {visit_count} Services',
        )

    # Bare "AMC" → use preferred visit_count or default 12 for society contracts
    if plan_l == 'amc' or plan_l.startswith('amc '):
        visit_count = preferred_visit_count or months or 12
        if visit_count <= 1:
            visit_count = 12
        visit_count = min(max(visit_count, 2), MAX_GENERATED_VISITS)
        unit, step = 'months', AMC_INTERVAL_MONTHS.get(visit_count, max(1, months // visit_count))
        return RecurringSpec(
            visit_count=visit_count,
            unit=unit,
            step=step,
            label=f'AMC {visit_count} Services',
        )

    # Calendar frequencies (Society quotation FREQ dropdown)
    for key, (unit, step) in CALENDAR_FREQUENCY_INTERVALS.items():
        if plan_l == key or plan_l.startswith(key + ' '):
            if unit == 'days':
                # ~4.345 weeks per month
                visit_count = max(1, int(round(months * 30.4375 / step)))
            else:
                visit_count = max(1, months // step)
            # Yearly over a 12‑month contract still needs a next-year follow-up
            # so Upcoming Services has something to show.
            if key in {'yearly', 'annual', 'annually'} and visit_count < 2:
                visit_count = 2
            visit_count = min(max(visit_count, 1), MAX_GENERATED_VISITS)
            if preferred_visit_count and preferred_visit_count > 1:
                visit_count = min(preferred_visit_count, MAX_GENERATED_VISITS)
            return RecurringSpec(
                visit_count=visit_count,
                unit=unit,
                step=step,
                label=key.title() if key != 'half yearly' else 'Half Yearly',
            )

    return None


def parse_amc_visit_count(plan: str) -> Optional[int]:
    """Backward-compatible: visit count for AMC / recurring plans, else None."""
    spec = resolve_recurring_spec(plan)
    return spec.visit_count if spec else None


def is_amc_plan(plan: str) -> bool:
    return resolve_recurring_spec(plan) is not None


def is_termite_service(service: str) -> bool:
    normalized = (service or '').lower()
    return 'termite' in normalized


def is_bed_bug_service(service: str) -> bool:
    normalized = (service or '').lower()
    return 'bed bug' in normalized or 'bedbug' in normalized


def interval_months_for_package(visit_count: int) -> int:
    return AMC_INTERVAL_MONTHS.get(visit_count, 4)


def amc_interval_spec(service: str, visit_count: int) -> tuple[str, int]:
    """
    Return ('months', n) or ('days', n) spacing for an AMC package.
    Mosquito 24/48 use day-based intervals; all other packages use months.
    """
    svc = (service or '').lower()
    if 'mosquito' in svc and visit_count in MOSQUITO_INTERVAL_DAYS:
        return 'days', MOSQUITO_INTERVAL_DAYS[visit_count]
    return 'months', interval_months_for_package(visit_count)


def visit_date_for_cycle(
    start_date: date,
    cycle_index: int,
    service: str,
    visit_count: int,
    *,
    unit: Optional[str] = None,
    step: Optional[int] = None,
) -> date:
    """cycle_index 0 = first visit on start_date."""
    if unit is None or step is None:
        unit, step = amc_interval_spec(service, visit_count)
    if unit == 'days':
        return start_date + timedelta(days=step * cycle_index)
    return start_date + relativedelta(months=step * cycle_index)


def visit_type_label(service: str, plan: str, cycle: int = 1) -> str:
    svc = (service or '').lower()
    recurring = is_amc_plan(plan)
    if is_termite_service(service):
        return 'TERMITE CHECK-UP' if cycle > 1 else 'TERMITE TREATMENT'
    if 'rodent' in svc:
        return 'RODENT AMC' if recurring else 'RODENT SERVICE'
    if 'mosquito' in svc:
        return 'MOSQUITO AMC' if recurring else 'MOSQUITO SERVICE'
    if 'cockroach' in svc or 'ants' in svc or 'general pest' in svc:
        return 'COCKROACH AMC' if recurring else 'COCKROACH SERVICE'
    if is_bed_bug_service(service):
        return 'BED BUG AMC' if recurring else 'BED BUG SERVICE'
    if recurring:
        return 'AMC VISIT'
    return 'SERVICE VISIT'


def build_visit_plans(
    service: str,
    plan: str,
    start_date: date,
    *,
    contract_months: Optional[int] = None,
    preferred_visit_count: Optional[int] = None,
) -> list[VisitPlan]:
    """Return all visit plans for a service line (cycle 1 = first visit on start_date)."""
    service = service or ''
    plan = plan or ''

    if is_termite_service(service):
        return [
            VisitPlan(
                cycle=i + 1,
                visit_date=start_date + relativedelta(months=TERMITE_CHECKUP_INTERVAL_MONTHS * i),
                visit_type='TERMITE TREATMENT' if i == 0 else 'TERMITE CHECK-UP',
                total_visits=TERMITE_TOTAL_VISITS,
            )
            for i in range(TERMITE_TOTAL_VISITS)
        ]

    spec = resolve_recurring_spec(
        plan,
        service=service,
        contract_months=contract_months,
        preferred_visit_count=preferred_visit_count,
    )
    if not spec:
        return [
            VisitPlan(
                cycle=1,
                visit_date=start_date,
                visit_type=visit_type_label(service, plan, 1),
                total_visits=1,
            )
        ]

    return [
        VisitPlan(
            cycle=i + 1,
            visit_date=visit_date_for_cycle(
                start_date,
                i,
                service,
                spec.visit_count,
                unit=spec.unit,
                step=spec.step,
            ),
            visit_type=visit_type_label(service, plan, i + 1),
            total_visits=spec.visit_count,
        )
        for i in range(spec.visit_count)
    ]


def calculate_next_visit_date(service: str, plan: str, schedule_date: date) -> tuple[Optional[date], int]:
    """Match legacy JobCardService.calculate_next_service_date for a single service line."""
    plans = build_visit_plans(service, plan, schedule_date)
    if len(plans) <= 1:
        return None, 1
    return plans[1].visit_date, plans[0].total_visits


class BookingScheduleEngine:
    @staticmethod
    def generate_all_visits(main_job) -> list[Any]:
        """Pre-generate all future visits for AMC / termite service lines."""
        from core.models import JobCard
        from core.jobcard_schedule import schedule_datetime_from_service_date

        if main_job.is_followup_visit or main_job.is_complaint_call:
            return []
        if not main_job.schedule_datetime:
            return []

        start_date = main_job.schedule_datetime.date()
        contract_months = parse_contract_months(getattr(main_job, 'contract_duration', None))
        preferred_visits = getattr(main_job, 'max_cycle', None) or None
        items = list(main_job.service_items or [])
        if not items and main_job.service_type:
            items = [
                {
                    'service': main_job.service_type,
                    'plan': '',
                    'area': main_job.bhk_size or '',
                    'amount': 0,
                }
            ]

        created: list[Any] = []
        earliest_next: Optional[date] = None
        root_max_cycle = main_job.max_cycle or 1

        for item in items:
            service = str(item.get('service') or '').strip()
            plan = str(item.get('plan') or item.get('frequency') or '').strip()
            if not service:
                continue

            plans = build_visit_plans(
                service,
                plan,
                start_date,
                contract_months=contract_months,
                preferred_visit_count=preferred_visits if preferred_visits and preferred_visits > 1 else None,
            )
            if not plans:
                continue

            root_max_cycle = max(root_max_cycle, plans[-1].total_visits)

            for spec in plans[1:]:
                if JobCard.objects.filter(
                    parent_job=main_job,
                    source_service=service,
                    service_cycle=spec.cycle,
                ).exists():
                    continue

                sched_dt = schedule_datetime_from_service_date(
                    spec.visit_date,
                    reference_datetime=main_job.schedule_datetime,
                    time_slot=main_job.time_slot,
                )

                is_amc = is_amc_plan(plan)
                child = JobCard(
                    client=main_job.client,
                    service_type=service,
                    service_items=[item],
                    service_category=(
                        JobCard.ServiceCategory.AMC
                        if is_amc
                        else main_job.service_category
                    ),
                    schedule_datetime=sched_dt,
                    time_slot=main_job.time_slot,
                    service_cycle=spec.cycle,
                    max_cycle=spec.total_visits,
                    parent_job=main_job,
                    source_service=service,
                    visit_type=spec.visit_type,
                    is_auto_generated=True,
                    commercial_type=main_job.commercial_type,
                    property_type=main_job.property_type,
                    job_type=main_job.job_type,
                    society_billing_type=main_job.society_billing_type,
                    bhk_size=item.get('area') or main_job.bhk_size,
                    contract_duration=main_job.contract_duration,
                    price='0',
                    total_amount=0,
                    paid_amount=0,
                    pending_amount=0,
                    client_address=main_job.client_address,
                    state=main_job.state,
                    city=main_job.city,
                    master_country=main_job.master_country,
                    master_state=main_job.master_state,
                    master_city=main_job.master_city,
                    master_location=main_job.master_location,
                    full_address=main_job.full_address,
                    reference=main_job.reference,
                    status=JobCard.JobStatus.UPCOMING,
                    payment_status=JobCard.PaymentStatus.PAID,
                    is_service_call=True,
                    is_followup_visit=True,
                    included_in_amc=is_amc,
                    created_by=main_job.created_by,
                    creation_source=JobCard.CreationSource.AMC_AUTO,
                )
                if spec.cycle < spec.total_visits:
                    child.next_service_date = plans[spec.cycle].visit_date
                child.save()
                created.append(child)
                logger.info(
                    'Auto-generated visit %s cycle %s/%s for booking %s',
                    child.code,
                    spec.cycle,
                    spec.total_visits,
                    main_job.code,
                )

            if len(plans) > 1:
                nd = plans[1].visit_date
                if earliest_next is None or nd < earliest_next:
                    earliest_next = nd

        update_fields: list[str] = []

        if root_max_cycle > (main_job.max_cycle or 1):
            main_job.max_cycle = root_max_cycle
            update_fields.append('max_cycle')

        if not main_job.service_cycle:
            main_job.service_cycle = 1
            update_fields.append('service_cycle')

        if items:
            first_service = str(items[0].get('service') or '')
            first_plan = str(items[0].get('plan') or items[0].get('frequency') or '')
            first_plans = build_visit_plans(
                first_service,
                first_plan,
                start_date,
                contract_months=contract_months,
                preferred_visit_count=preferred_visits if preferred_visits and preferred_visits > 1 else None,
            )
            if first_plans and not main_job.visit_type:
                main_job.visit_type = first_plans[0].visit_type
                update_fields.append('visit_type')
            if first_service and not main_job.source_service:
                main_job.source_service = first_service
                update_fields.append('source_service')

        if earliest_next and not main_job.next_service_date:
            main_job.next_service_date = earliest_next
            update_fields.append('next_service_date')

        # Recurring society / AMC main bookings should be flagged for tab sync
        if root_max_cycle > 1 and not main_job.is_amc_main_booking:
            main_job.is_amc_main_booking = True
            update_fields.append('is_amc_main_booking')
        if root_max_cycle > 1 and main_job.service_category != JobCard.ServiceCategory.AMC:
            main_job.service_category = JobCard.ServiceCategory.AMC
            update_fields.append('service_category')

        if update_fields:
            main_job.save(update_fields=list(dict.fromkeys(update_fields)))

        return created

    @staticmethod
    def update_after_completion(completed_job) -> None:
        """Point completed / root bookings at the next pending auto-generated visit."""
        from core.models import JobCard

        root = completed_job.parent_job or completed_job

        if completed_job.parent_job and completed_job.source_service:
            next_in_chain = (
                JobCard.objects.filter(
                    parent_job=root,
                    source_service=completed_job.source_service,
                    status=JobCard.JobStatus.UPCOMING,
                    service_cycle__gt=completed_job.service_cycle or 0,
                )
                .order_by('service_cycle')
                .first()
            )
            next_date = None
            if next_in_chain and next_in_chain.schedule_datetime:
                next_date = next_in_chain.schedule_datetime.date()
            elif next_in_chain and next_in_chain.next_service_date:
                next_date = next_in_chain.next_service_date
            if next_date and completed_job.next_service_date != next_date:
                completed_job.next_service_date = next_date
                completed_job.save(update_fields=['next_service_date'])

        upcoming = (
            JobCard.objects.filter(Q(id=root.id) | Q(parent_job=root))
            .filter(status=JobCard.JobStatus.UPCOMING)
            .exclude(id=completed_job.id)
            .order_by('schedule_datetime', 'service_cycle')
        )
        next_job = upcoming.first()
        if next_job and next_job.schedule_datetime:
            root_date = next_job.schedule_datetime.date()
            if root.next_service_date != root_date:
                root.next_service_date = root_date
                root.save(update_fields=['next_service_date'])

    @staticmethod
    def service_timeline_for(jobcard) -> list[dict[str, Any]]:
        """Ordered visit list for a booking root (main + auto-generated children)."""
        from core.models import JobCard

        root = jobcard
        if jobcard.parent_job_id:
            root = JobCard.objects.filter(id=jobcard.parent_job_id).first() or jobcard

        visits = (
            JobCard.objects.filter(Q(id=root.id) | Q(parent_job=root))
            .order_by('source_service', 'service_cycle', 'schedule_datetime')
        )

        rows: list[dict[str, Any]] = []
        for visit in visits:
            rows.append(
                {
                    'id': visit.id,
                    'code': visit.code,
                    'service_name': visit.source_service or visit.service_type,
                    'visit_number': visit.service_cycle,
                    'total_visits': visit.max_cycle,
                    'visit_type': visit.visit_type,
                    'scheduled_date': (
                        visit.schedule_datetime.date().isoformat()
                        if visit.schedule_datetime
                        else None
                    ),
                    'next_scheduled_date': (
                        visit.next_service_date.isoformat()
                        if visit.next_service_date
                        else None
                    ),
                    'status': visit.status,
                    'technician_name': (
                        visit.technician.name if visit.technician_id else visit.assigned_to
                    ),
                    'completed_at': (
                        visit.completed_at.isoformat() if visit.completed_at else None
                    ),
                    'is_auto_generated': visit.is_auto_generated,
                }
            )
        return rows
