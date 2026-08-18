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

TERMITE_TOTAL_VISITS = 1  # Product rule: Termite = One-Time only (no checkup chain)
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


_OTHER_PEST_MARKERS = (
    'cockroach',
    'ant',
    'mosquito',
    'rodent',
    'bed bug',
    'bedbug',
    'lizard',
    'general pest',
)


def is_termite_only_service(service: str) -> bool:
    """True when the line is Termite alone (not a multi-pest package)."""
    if not is_termite_service(service):
        return False
    normalized = (service or '').lower()
    return not any(marker in normalized for marker in _OTHER_PEST_MARKERS)


def is_fixed_visit_service(service: str) -> bool:
    """Services with hard-coded visit counts that must never become AMC packages."""
    return is_termite_service(service) or is_bed_bug_service(service)


def fixed_visit_count_for_service(service: str) -> Optional[int]:
    """Return locked visit count when the service has a hard product rule."""
    if is_termite_service(service):
        return 1
    if is_bed_bug_service(service):
        return 2
    return None


def enforce_fixed_service_rules_on_job(job) -> list[str]:
    """
    Force Termite-only = One-Time (1 visit, never AMC) and Bed Bugs = 2 services max.

    Returns list of field names that were changed (caller may save).
    """
    from core.models import JobCard

    texts = [
        job.service_type or '',
        job.source_service or '',
        job.visit_type or '',
    ]
    items = job.service_items if isinstance(getattr(job, 'service_items', None), list) else []
    for item in items:
        texts.append(str((item or {}).get('service') or ''))

    blob = ' '.join(texts)
    # Prefer the dedicated line name so multi-pest shells are not forced to Termite rules.
    primary = (job.source_service or job.service_type or blob or '').strip()
    changed: list[str] = []

    if is_termite_only_service(primary) or (
        is_termite_only_service(blob) and not any(m in blob.lower() for m in _OTHER_PEST_MARKERS)
    ):
        if job.service_category != JobCard.ServiceCategory.ONE_TIME:
            job.service_category = JobCard.ServiceCategory.ONE_TIME
            changed.append('service_category')
        if job.is_amc_main_booking:
            job.is_amc_main_booking = False
            changed.append('is_amc_main_booking')
        if job.included_in_amc:
            job.included_in_amc = False
            changed.append('included_in_amc')
        if job.is_followup_visit:
            job.is_followup_visit = False
            changed.append('is_followup_visit')
        if job.is_service_call:
            job.is_service_call = False
            changed.append('is_service_call')
        if (job.max_cycle or 0) != 1:
            job.max_cycle = 1
            changed.append('max_cycle')
        if (job.planned_visit_count or 0) != 1:
            job.planned_visit_count = 1
            changed.append('planned_visit_count')
        if (job.service_cycle or 0) not in (0, 1):
            job.service_cycle = 1
            changed.append('service_cycle')
        if job.booking_type != JobCard.BookingType.NEW_BOOKING:
            job.booking_type = JobCard.BookingType.NEW_BOOKING
            changed.append('booking_type')
        if (job.visit_type or '').upper().find('CHECK') >= 0:
            job.visit_type = 'TERMITE TREATMENT'
            changed.append('visit_type')

    if is_bed_bug_service(blob) and not is_termite_service(blob):
        # Bed Bugs is a 2-service package, not an AMC subscription.
        if job.service_category == JobCard.ServiceCategory.AMC:
            job.service_category = JobCard.ServiceCategory.ONE_TIME
            changed.append('service_category')
        if job.is_amc_main_booking:
            job.is_amc_main_booking = False
            changed.append('is_amc_main_booking')
        if (job.max_cycle or 0) != 2:
            job.max_cycle = 2
            changed.append('max_cycle')
        if (job.planned_visit_count or 0) != 2:
            job.planned_visit_count = 2
            changed.append('planned_visit_count')
        if not job.service_cycle:
            job.service_cycle = 1
            changed.append('service_cycle')
        # Root / first visit must not stay flagged as a free follow-up.
        if not job.parent_job_id and (job.service_cycle or 1) <= 1:
            if job.is_followup_visit:
                job.is_followup_visit = False
                changed.append('is_followup_visit')
            if job.included_in_amc:
                job.included_in_amc = False
                changed.append('included_in_amc')

    return list(dict.fromkeys(changed))


def job_includes_bed_bugs(job) -> bool:
    """True when this JobCard is a Bed Bugs line or a package that includes one."""
    if is_bed_bug_service(getattr(job, 'service_type', None) or ''):
        return True
    if is_bed_bug_service(getattr(job, 'source_service', None) or ''):
        return True
    if is_bed_bug_service(getattr(job, 'visit_type', None) or ''):
        return True
    items = getattr(job, 'service_items', None)
    if isinstance(items, list):
        for item in items:
            if is_bed_bug_service(str((item or {}).get('service') or '')):
                return True
    return False


def heal_bed_bug_package(job) -> list[Any]:
    """
    Repair an existing Bed Bugs booking saved as One-Time / 1 visit.

    Locks max_cycle + planned_visit_count to 2 and creates the missing
    ~15-day follow-up JobCard. Idempotent.
    """
    from core.models import JobCard
    from core.payout_engine import calculate_and_apply_payout

    if job is None:
        return []

    root = job.parent_job or job
    if getattr(root, 'status', None) == JobCard.JobStatus.CANCELLED:
        return []
    if not job_includes_bed_bugs(root) and not job_includes_bed_bugs(job):
        return []

    changed = enforce_fixed_service_rules_on_job(root)
    if changed:
        root.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))

    created = BookingScheduleEngine.generate_all_visits(root)
    try:
        root.refresh_from_db()
    except Exception:
        pass

    children = JobCard.objects.filter(parent_job=root).exclude(
        status=JobCard.JobStatus.CANCELLED,
    )
    for child in children:
        if not job_includes_bed_bugs(child):
            continue
        child_changed = enforce_fixed_service_rules_on_job(child)
        if child_changed:
            child.save(update_fields=list(dict.fromkeys(child_changed + ['updated_at'])))

    if (
        changed
        and root.status == JobCard.JobStatus.DONE
        and root.payout_status != JobCard.PayoutStatus.LEGACY_EXEMPT
        and job_includes_bed_bugs(root)
        and not is_multi_service_booking(root)
    ):
        calculate_and_apply_payout(root, force=True)

    return created


def heal_all_bed_bug_packages(*, dry: bool = False) -> dict[str, int]:
    """Sweep every non-cancelled Bed Bugs root booking and backfill visit 2."""
    from core.models import JobCard

    qs = (
        JobCard.objects.filter(parent_job__isnull=True)
        .exclude(status=JobCard.JobStatus.CANCELLED)
        .filter(
            Q(service_type__icontains='bed')
            | Q(source_service__icontains='bed')
            | Q(visit_type__icontains='bed')
        )
    )
    scanned = 0
    healed = 0
    created_visits = 0
    for job in qs.iterator():
        if not job_includes_bed_bugs(job):
            continue
        scanned += 1
        has_second = JobCard.objects.filter(
            parent_job=job,
            service_cycle=2,
        ).exclude(status=JobCard.JobStatus.CANCELLED).filter(
            Q(source_service__icontains='bed')
            | Q(service_type__icontains='bed')
            | Q(visit_type__icontains='bed')
        ).exists()
        single = not is_multi_service_booking(job)
        flags_wrong = single and (
            (job.max_cycle or 0) != 2 or (job.planned_visit_count or 0) != 2
        )
        needs_followup = bool(job.schedule_datetime) and not has_second
        if not flags_wrong and not needs_followup:
            continue
        healed += 1
        if dry:
            continue
        created = heal_bed_bug_package(job)
        created_visits += len(created)
    return {
        'scanned': scanned,
        'healed': healed,
        'created_visits': created_visits,
    }


def sync_plan_flags_from_service_items(job) -> list[str]:
    """
    When CRM edits service_items (e.g. AMC → One-Time), clear stale AMC flags
    and cancel leftover AMC follow-up children that no longer match the plan.
    """
    from core.models import JobCard

    if job.parent_job_id:
        return []

    items = job.service_items if isinstance(getattr(job, 'service_items', None), list) else []
    if not items:
        return []

    changed: list[str] = []
    has_amc_line = False
    for item in items:
        svc = str((item or {}).get('service') or '').strip()
        plan = str((item or {}).get('plan') or (item or {}).get('frequency') or '').strip()
        if svc and is_amc_plan(plan) and not is_fixed_visit_service(svc):
            has_amc_line = True
            break

    names = service_line_names(items)
    if len(names) == 1 and names[0]:
        if (job.source_service or '') != names[0]:
            job.source_service = names[0]
            changed.append('source_service')
        if ',' in (job.service_type or '') or (
            job.service_type and names[0].lower() not in (job.service_type or '').lower()
            and len((job.service_type or '').split(',')) > 1
        ):
            job.service_type = names[0]
            changed.append('service_type')

    if not has_amc_line:
        if job.is_amc_main_booking:
            job.is_amc_main_booking = False
            changed.append('is_amc_main_booking')
        if job.service_category == JobCard.ServiceCategory.AMC:
            job.service_category = JobCard.ServiceCategory.ONE_TIME
            changed.append('service_category')
        if job.booking_type in (
            JobCard.BookingType.AMC_MAIN,
            JobCard.BookingType.AMC_FOLLOWUP,
        ):
            job.booking_type = JobCard.BookingType.NEW_BOOKING
            changed.append('booking_type')
        if job.included_in_amc:
            job.included_in_amc = False
            changed.append('included_in_amc')

        # Cancel leftover AMC follow-ups (cycle > 1) that no longer apply.
        # Keep Bed Bugs service-2 children (cycle 2, not AMC).
        qs = JobCard.objects.filter(
            parent_job=job,
            service_cycle__gt=1,
            status__in=[JobCard.JobStatus.UPCOMING, JobCard.JobStatus.PENDING],
        ).exclude(
            Q(service_type__icontains='bed') | Q(source_service__icontains='bed')
        ).filter(
            Q(included_in_amc=True)
            | Q(is_followup_visit=True)
            | Q(booking_type=JobCard.BookingType.AMC_FOLLOWUP)
            | Q(visit_type__icontains='AMC')
        )
        qs.update(status=JobCard.JobStatus.CANCELLED)

    changed.extend(enforce_fixed_service_rules_on_job(job))
    return list(dict.fromkeys(changed))


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
    recurring = is_amc_plan(plan) and not is_fixed_visit_service(service)
    if is_termite_service(service):
        # Termite is One-Time only — never label checkup / AMC follow-ups.
        return 'TERMITE TREATMENT'
    if 'rodent' in svc:
        return 'RODENT AMC' if recurring else 'RODENT SERVICE'
    if 'mosquito' in svc:
        return 'MOSQUITO AMC' if recurring else 'MOSQUITO SERVICE'
    if 'cockroach' in svc or 'ants' in svc or 'general pest' in svc:
        return 'COCKROACH AMC' if recurring else 'COCKROACH SERVICE'
    if is_bed_bug_service(service):
        return 'BED BUG SERVICE'
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

    # HARD RULE: Termite = One-Time only (ignore AMC / preferred visit count).
    if is_termite_service(service):
        return [
            VisitPlan(
                cycle=1,
                visit_date=start_date,
                visit_type='TERMITE TREATMENT',
                total_visits=1,
            )
        ]

    # HARD RULE: Bed Bugs = exactly 2 services (day 0 + ~15 days). Never AMC chain.
    if is_bed_bug_service(service):
        second = start_date + timedelta(days=15)
        return [
            VisitPlan(
                cycle=1,
                visit_date=start_date,
                visit_type='BED BUG SERVICE',
                total_visits=2,
            ),
            VisitPlan(
                cycle=2,
                visit_date=second,
                visit_type='BED BUG SERVICE',
                total_visits=2,
            ),
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


def service_line_names(job_or_items) -> list[str]:
    """Distinct non-empty service names from a JobCard or service_items list."""
    if isinstance(job_or_items, list):
        items = job_or_items
    else:
        items = list(getattr(job_or_items, 'service_items', None) or [])
        if not items and getattr(job_or_items, 'service_type', None):
            return [str(job_or_items.service_type).strip()]
    names: list[str] = []
    for item in items:
        name = str((item or {}).get('service') or '').strip()
        if name and name not in names:
            names.append(name)
    return names


def is_multi_service_booking(job) -> bool:
    """True when the root booking has 2+ service lines (package shell)."""
    if getattr(job, 'parent_job_id', None):
        return False
    return len(service_line_names(job)) > 1


def is_multi_service_package_shell(job) -> bool:
    """
    Multi-service root whose day-1 work was split into per-service JobCards.
    Shell holds payment / customer total; technician ledger uses the children.
    """
    if not is_multi_service_booking(job):
        return False
    from core.models import JobCard

    return JobCard.objects.filter(parent_job_id=job.id, service_cycle=1).exists()


class BookingScheduleEngine:
    @staticmethod
    def sync_multi_service_day1_children(main_job, *, completing: bool = False) -> list[Any]:
        """
        Keep day-1 per-service visits in sync with the package shell.

        Crew rule: each service line keeps its own technician. The package
        technician is copied only onto lines that were never assigned. Completing
        the shell must not overwrite Akshay on Cockroach with Mustafa from Termite.
        """
        from django.utils import timezone

        from core.models import JobCard, JobCardTechnicianParticipation
        from core.payout_engine import ensure_lead_participation

        if not is_multi_service_booking(main_job):
            return []

        # Legacy multi packages often only generated follow-up cycles (2+) —
        # create missing day-1 rows first so ledger can split per service.
        BookingScheduleEngine.backfill_missing_day1_children(main_job)

        # When completing the shell, include Cancelled day-1 rows so we can
        # revive them (CRM cancel often cascades to children while the tech
        # is still finishing the visit). Otherwise skip Cancelled shells.
        day1_qs = JobCard.objects.filter(parent_job=main_job, service_cycle=1)
        if not completing:
            day1_qs = day1_qs.exclude(status=JobCard.JobStatus.CANCELLED)
        children = list(day1_qs.prefetch_related('technician_participations'))
        shell_parts = list(main_job.technician_participations.all())
        synced: list[Any] = []
        for child in children:
            update_fields: list[str] = []
            has_own_crew = bool(child.technician_id) or any(
                True for _ in child.technician_participations.all()
            )

            if not has_own_crew:
                if main_job.technician_id:
                    child.technician_id = main_job.technician_id
                    update_fields.append('technician')
                if main_job.partner_id:
                    child.partner_id = main_job.partner_id
                    update_fields.append('partner')
                if main_job.assigned_to:
                    child.assigned_to = main_job.assigned_to
                    update_fields.append('assigned_to')

            if completing and child.status != JobCard.JobStatus.DONE:
                child.status = JobCard.JobStatus.DONE
                child.completed_at = main_job.completed_at or timezone.now()
                update_fields.extend(['status', 'completed_at'])
                if main_job.payment_model and child.payment_model != main_job.payment_model:
                    child.payment_model = main_job.payment_model
                    update_fields.append('payment_model')
            if update_fields:
                child.save(update_fields=list(dict.fromkeys(update_fields + ['updated_at'])))

            if has_own_crew:
                ensure_lead_participation(child)
            else:
                for part in shell_parts:
                    JobCardTechnicianParticipation.objects.update_or_create(
                        jobcard=child,
                        technician_id=part.technician_id,
                        defaults={
                            'partner_id': part.partner_id,
                            'role': part.role,
                            'attendance_status': part.attendance_status,
                            'is_payout_eligible': part.is_payout_eligible,
                            'checked_in_at': part.checked_in_at,
                            'checked_out_at': part.checked_out_at,
                        },
                    )
                ensure_lead_participation(child)

            if completing and child.status == JobCard.JobStatus.DONE:
                from core.payout_engine import try_apply_payout_after_completion

                try_apply_payout_after_completion(child)
            synced.append(child)
        return synced

    @staticmethod
    def backfill_missing_day1_children(main_job) -> list[Any]:
        """
        Create cycle-1 per-service JobCards when a multi-service package only has
        follow-up children (legacy bug). Safe to call repeatedly.
        """
        from django.utils import timezone

        from core.jobcard_schedule import schedule_datetime_from_service_date
        from core.models import JobCard, JobCardTechnicianParticipation
        from core.payment_utils import parse_jobcard_price
        from core.payout_engine import revenue_fields_from_parent

        if main_job.parent_job_id or not is_multi_service_booking(main_job):
            return []
        if not main_job.schedule_datetime:
            return []

        items = list(main_job.service_items or [])
        if len(service_line_names(items)) < 2:
            return []

        start_date = main_job.schedule_datetime.date()
        contract_months = parse_contract_months(getattr(main_job, 'contract_duration', None))
        created: list[Any] = []

        for item in items:
            service = str(item.get('service') or '').strip()
            plan = str(item.get('plan') or item.get('frequency') or '').strip()
            if not service:
                continue
            # UniqueConstraint(parent, source_service, service_cycle) applies
            # even when the existing day-1 row is Cancelled — never insert a
            # second row for the same key (that poisoned partner End Service).
            if JobCard.objects.filter(
                parent_job=main_job,
                source_service=service,
                service_cycle=1,
            ).exists():
                continue

            preferred = None
            preferred_visits = getattr(main_job, 'max_cycle', None) or None
            if (
                not is_fixed_visit_service(service)
                and preferred_visits
                and preferred_visits > 1
            ):
                preferred = preferred_visits

            plans = build_visit_plans(
                service,
                plan,
                start_date,
                contract_months=contract_months,
                preferred_visit_count=preferred,
            )
            if not plans:
                # One-time line with empty plan — still need a day-1 ledger row.
                plans = [
                    VisitPlan(
                        cycle=1,
                        visit_date=start_date,
                        visit_type=f'{service.upper()} SERVICE',
                        total_visits=fixed_visit_count_for_service(service) or 1,
                    )
                ]
            locked = fixed_visit_count_for_service(service)
            if locked is not None:
                plans = plans[:locked]
            spec = plans[0]
            is_amc = is_amc_plan(plan) and not is_fixed_visit_service(service)
            line_amount = parse_jobcard_price(item.get('amount'))
            sched_dt = schedule_datetime_from_service_date(
                spec.visit_date,
                reference_datetime=main_job.schedule_datetime,
                time_slot=main_job.time_slot,
            )
            child_status = (
                JobCard.JobStatus.DONE
                if main_job.status == JobCard.JobStatus.DONE
                else JobCard.JobStatus.PENDING
            )
            child = JobCard(
                client=main_job.client,
                service_type=service,
                service_items=[item],
                service_category=(
                    JobCard.ServiceCategory.AMC if is_amc else JobCard.ServiceCategory.ONE_TIME
                ),
                schedule_datetime=sched_dt,
                time_slot=main_job.time_slot,
                service_cycle=1,
                max_cycle=spec.total_visits,
                planned_visit_count=spec.total_visits,
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
                price=str(line_amount) if line_amount > 0 else '0',
                total_amount=line_amount if line_amount > 0 else 0,
                paid_amount=line_amount if line_amount > 0 else 0,
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
                technician=main_job.technician,
                partner=main_job.partner,
                assigned_to=main_job.assigned_to or '',
                status=child_status,
                completed_at=(
                    main_job.completed_at or timezone.now()
                    if child_status == JobCard.JobStatus.DONE
                    else None
                ),
                payment_status=JobCard.PaymentStatus.PAID,
                is_service_call=False,
                is_followup_visit=False,
                included_in_amc=False,
                created_by=main_job.created_by,
                creation_source=JobCard.CreationSource.AMC_AUTO,
            )
            rev = revenue_fields_from_parent(main_job)
            rev.pop('planned_visit_count', None)
            rev['payout_status'] = JobCard.PayoutStatus.NOT_APPLICABLE
            for key, value in rev.items():
                setattr(child, key, value)
            enforce_fixed_service_rules_on_job(child)
            child.save()
            for part in main_job.technician_participations.all():
                JobCardTechnicianParticipation.objects.update_or_create(
                    jobcard=child,
                    technician_id=part.technician_id,
                    defaults={
                        'partner_id': part.partner_id,
                        'role': part.role,
                        'attendance_status': part.attendance_status,
                        'is_payout_eligible': part.is_payout_eligible,
                        'checked_in_at': part.checked_in_at,
                        'checked_out_at': part.checked_out_at,
                    },
                )
            created.append(child)
            logger.info(
                'Backfilled day-1 visit %s for %s under package %s',
                child.id,
                service,
                main_job.id,
            )

        if created and main_job.visit_type != 'MULTI SERVICE PACKAGE':
            main_job.visit_type = 'MULTI SERVICE PACKAGE'
            main_job.save(update_fields=['visit_type', 'updated_at'])
        return created

    @staticmethod
    def generate_all_visits(main_job) -> list[Any]:
        """Pre-generate visits. Multi-service bookings get day-1 rows per service line."""
        from core.models import JobCard
        from core.jobcard_schedule import schedule_datetime_from_service_date
        from core.payment_utils import parse_jobcard_price

        # Lock Termite / Bed Bugs fields first so a root wrongly flagged as a
        # follow-up still gets its 2nd visit generated.
        if not getattr(main_job, 'parent_job_id', None):
            fixed_fields = enforce_fixed_service_rules_on_job(main_job)
            if fixed_fields:
                main_job.save(update_fields=list(dict.fromkeys(fixed_fields + ['updated_at'])))

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

        # Multi-service package: create cycle-1 JobCards per line so the ledger
        # shows Cockroach / Bed Bugs / Mosquito separately (not one combined row).
        is_multi = len(service_line_names(items)) > 1

        created: list[Any] = []
        earliest_next: Optional[date] = None
        root_max_cycle = main_job.max_cycle or 1
        has_true_amc_line = False

        for item in items:
            service = str(item.get('service') or '').strip()
            plan = str(item.get('plan') or item.get('frequency') or '').strip()
            if not service:
                continue

            # Never pass preferred AMC visit counts into Termite / Bed Bugs.
            preferred_for_line = None
            if (
                not is_fixed_visit_service(service)
                and preferred_visits
                and preferred_visits > 1
            ):
                preferred_for_line = preferred_visits

            plans = build_visit_plans(
                service,
                plan,
                start_date,
                contract_months=contract_months,
                preferred_visit_count=preferred_for_line,
            )
            if not plans:
                continue

            # Absolute caps — Termite 1, Bed Bugs 2 (never more).
            locked = fixed_visit_count_for_service(service)
            if locked is not None:
                plans = plans[:locked]

            root_max_cycle = max(root_max_cycle, plans[-1].total_visits)
            is_amc = is_amc_plan(plan) and not is_fixed_visit_service(service)
            if is_amc:
                has_true_amc_line = True

            # Single-service: main IS cycle 1 → only create follow-ups (plans[1:]).
            # Multi-service: also create cycle 1 per line (package shell is not payable).
            specs = plans if is_multi else plans[1:]
            line_amount = parse_jobcard_price(item.get('amount'))

            for spec in specs:
                if locked is not None and spec.cycle > locked:
                    break
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

                is_day1 = spec.cycle == 1 and is_multi
                child_price = line_amount if is_day1 else parse_jobcard_price('0')
                if is_day1:
                    # Same operational day as the package shell.
                    child_status = (
                        main_job.status
                        if main_job.status
                        not in (JobCard.JobStatus.DONE, JobCard.JobStatus.CANCELLED)
                        else JobCard.JobStatus.PENDING
                    )
                    if child_status == JobCard.JobStatus.UPCOMING:
                        child_status = JobCard.JobStatus.PENDING
                else:
                    child_status = JobCard.JobStatus.UPCOMING

                child = JobCard(
                    client=main_job.client,
                    service_type=service,
                    service_items=[item],
                    service_category=(
                        JobCard.ServiceCategory.AMC
                        if is_amc
                        else JobCard.ServiceCategory.ONE_TIME
                    ),
                    schedule_datetime=sched_dt,
                    time_slot=main_job.time_slot,
                    service_cycle=spec.cycle,
                    max_cycle=spec.total_visits,
                    planned_visit_count=spec.total_visits,
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
                    price=str(child_price) if child_price > 0 else '0',
                    total_amount=child_price if child_price > 0 else 0,
                    paid_amount=child_price if is_day1 and child_price > 0 else 0,
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
                    technician=main_job.technician if is_day1 else None,
                    partner=main_job.partner if is_day1 else None,
                    assigned_to=main_job.assigned_to if is_day1 else '',
                    status=child_status,
                    payment_status=JobCard.PaymentStatus.PAID,
                    is_service_call=not is_day1,
                    is_followup_visit=not is_day1,
                    # Day-1 AMC line under a package = that line's "main" visit
                    # (not AMC_FOLLOWUP), so CRM keeps it in Pending with the shell.
                    included_in_amc=bool(is_amc and not is_day1),
                    created_by=main_job.created_by,
                    creation_source=JobCard.CreationSource.AMC_AUTO,
                )
                from core.payout_engine import revenue_fields_from_parent

                rev = revenue_fields_from_parent(main_job)
                # Keep this line's own visit count — never inherit package max_cycle.
                rev.pop('planned_visit_count', None)
                # Fresh visit — never inherit locked/legacy payout state from the shell.
                rev['payout_status'] = JobCard.PayoutStatus.NOT_APPLICABLE
                for key, value in rev.items():
                    setattr(child, key, value)
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

        if is_multi:
            if main_job.visit_type != 'MULTI SERVICE PACKAGE':
                main_job.visit_type = 'MULTI SERVICE PACKAGE'
                update_fields.append('visit_type')
        elif items:
            first_service = str(items[0].get('service') or '')
            first_plan = str(items[0].get('plan') or items[0].get('frequency') or '')
            first_plans = build_visit_plans(
                first_service,
                first_plan,
                start_date,
                contract_months=contract_months,
                preferred_visit_count=(
                    preferred_visits
                    if preferred_visits and preferred_visits > 1 and not is_fixed_visit_service(first_service)
                    else None
                ),
            )
            if first_plans and not main_job.visit_type:
                main_job.visit_type = first_plans[0].visit_type
                update_fields.append('visit_type')
            # Never overwrite a clean single-service name with a multi-pest blob.
            if first_service and (
                not main_job.source_service
                or ',' in (main_job.source_service or '')
            ):
                main_job.source_service = first_service
                update_fields.append('source_service')

        if earliest_next and not main_job.next_service_date:
            main_job.next_service_date = earliest_next
            update_fields.append('next_service_date')

        # Only real AMC lines become AMC main — never Termite or Bed Bugs packages.
        termite_main = is_termite_service(main_job.service_type or '') or is_termite_service(
            main_job.source_service or ''
        )
        bed_bug_main = is_bed_bug_service(main_job.service_type or '') or is_bed_bug_service(
            main_job.source_service or ''
        )
        if (
            has_true_amc_line
            and root_max_cycle > 1
            and not termite_main
            and not bed_bug_main
            and not main_job.is_amc_main_booking
        ):
            main_job.is_amc_main_booking = True
            update_fields.append('is_amc_main_booking')
        if (
            has_true_amc_line
            and root_max_cycle > 1
            and not termite_main
            and not bed_bug_main
            and main_job.service_category != JobCard.ServiceCategory.AMC
        ):
            main_job.service_category = JobCard.ServiceCategory.AMC
            update_fields.append('service_category')

        # Re-apply hard locks after cycle updates.
        update_fields.extend(enforce_fixed_service_rules_on_job(main_job))

        if update_fields:
            main_job.save(update_fields=list(dict.fromkeys(update_fields + ['updated_at'])))

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
