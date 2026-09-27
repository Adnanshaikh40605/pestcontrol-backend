"""Match a technician's service eligibility to a booking.

A technician is eligible only when both axes match:

* category — One-Time vs AMC, from the booking's existing service category
  and per-line plan (``service_items.plan`` / ``frequency`` / ``service_mode``).
* type — Standard vs Premium, from the service name (Cockroach Standard vs
  Cockroach Premium) or an explicit standard/premium flag on that service.

Jobs that are neither clearly Standard nor Premium stay visible to every
technician who matches the One-Time/AMC category. See ``line_tiers``.

Existing technicians: all four flags default True (migration 0118) so they
do not lose jobs. New technicians: the CRM form also starts with all four
checked; staff uncheck what this person should not receive. API creates
that omit the fields inherit the model default (all True).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import SimpleNamespace

_TIER_WORD = re.compile(r'\b(standard|premium)\b', re.IGNORECASE)

# Keys a service line may already use for treatment quality. Job-level
# package_tier is NOT in this list — it often defaults to "standard" on
# bookings that are not a Standard product (Bed Bugs, Integrated IPM, …).
_LINE_TIER_KEYS = ('package_tier', 'treatment_quality', 'quality', 'tier')

_PREVIEW_FIELDS = (
    'service_category',
    'service_type',
    'service_items',
    'package_tier',
    'booking_type',
    'source_service',
    'included_in_amc',
    'is_amc_main_booking',
    'is_followup_visit',
    'visit_type',
)


@dataclass(frozen=True)
class JobServiceRequirements:
    categories: frozenset[str]
    tiers: frozenset[str]


def _normalize_tier_token(raw) -> str | None:
    text = str(raw or '').strip().lower()
    if text in ('standard', 'premium'):
        return text
    return None


def _tiers_in_label(label: str) -> set[str]:
    return {m.group(1).lower() for m in _TIER_WORD.finditer(label or '')}


def category_from_plan(plan: str | None) -> str | None:
    """One-Time vs AMC from an existing plan / service-mode label.

    Returns None when the label is blank or not a known mode, so the caller
    falls back to the booking's service category.
    """
    text = (plan or '').strip()
    if not text:
        return None
    folded = text.lower().replace('_', ' ').replace('-', ' ')
    folded = ' '.join(folded.split())
    if 'one time' in folded or folded in {'ot', 'onetime'}:
        return 'one_time'
    from core.booking_schedule_engine import is_amc_plan

    if is_amc_plan(text) or 'amc' in folded:
        return 'amc'
    return None


def job_level_category(job) -> str:
    """One-Time vs AMC from the booking's existing category / AMC flags."""
    from core.models import JobCard

    if getattr(job, 'service_category', None) == JobCard.ServiceCategory.AMC:
        return 'amc'
    booking_type = getattr(job, 'booking_type', None) or ''
    if booking_type in (
        JobCard.BookingType.AMC_MAIN,
        JobCard.BookingType.AMC_FOLLOWUP,
    ):
        return 'amc'
    if getattr(job, 'is_amc_main_booking', False) or getattr(job, 'included_in_amc', False):
        return 'amc'
    return 'one_time'


def line_tiers(name: str, item: dict | None, job) -> set[str]:
    """Standard and/or Premium required by one service line.

    Unscoped lines return an empty set. Integrated IPM, bed bugs, rodent
    systems (Regular Rodent, Kill-Rodent System), termite, mosquito fogging,
    and similar packages are not Standard or Premium products. They stay
    eligible for any technician who matches the One-Time/AMC category, unless
    that service line already carries an explicit standard/premium flag
    (``package_tier`` / ``treatment_quality`` / ``quality`` / ``tier`` on the
    line). A booking-level ``package_tier`` is used only to disambiguate the
    cockroach family when the stored name is still the legacy label
    ("Cockroach / Ants") and does not itself say Standard or Premium.
    """
    if item:
        flagged: set[str] = set()
        for key in _LINE_TIER_KEYS:
            token = _normalize_tier_token(item.get(key))
            if token:
                flagged.add(token)
        if flagged:
            return flagged

    named = _tiers_in_label(name)
    if named:
        return named

    from core.pricing.aliases import is_cockroach_family

    if name and is_cockroach_family(name):
        job_tier = _normalize_tier_token(getattr(job, 'package_tier', None))
        if job_tier:
            return {job_tier}
    return set()


def iter_service_lines(job):
    """Yield (service name, plan label, item dict or None) for a booking."""
    items = getattr(job, 'service_items', None) or []
    if isinstance(items, list) and items:
        emitted = False
        for raw in items:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get('service') or '').strip()
            plan = str(
                raw.get('plan')
                or raw.get('frequency')
                or raw.get('service_mode')
                or ''
            ).strip()
            if not name and not plan:
                continue
            emitted = True
            yield name, plan, raw
        if emitted:
            return

    source = str(getattr(job, 'source_service', None) or '').strip()
    if source:
        yield source, '', None
        return

    blob = str(getattr(job, 'service_type', None) or '')
    parts = [p.strip() for p in re.split(r'[,|]+', blob) if p and p.strip()]
    if parts:
        for part in parts:
            yield part, '', None
        return

    yield '', '', None


def job_service_requirements(job) -> JobServiceRequirements:
    categories: set[str] = set()
    tiers: set[str] = set()
    for name, plan, item in iter_service_lines(job):
        category = category_from_plan(plan)
        if category is None:
            category = job_level_category(job)
        categories.add(category)
        tiers |= line_tiers(name, item, job)
    if not categories:
        categories.add(job_level_category(job))
    return JobServiceRequirements(frozenset(categories), frozenset(tiers))


def _flag(technician, name: str) -> bool:
    # Missing attribute (unsaved stubs) matches the model default: enabled.
    return bool(getattr(technician, name, True))


def technician_eligible_for_job(technician, job) -> bool:
    """True when this technician may be offered or assigned the booking."""
    if technician is None or job is None:
        return True
    req = job_service_requirements(job)
    if 'one_time' in req.categories and not _flag(technician, 'accepts_one_time_jobs'):
        return False
    if 'amc' in req.categories and not _flag(technician, 'accepts_amc_jobs'):
        return False
    if 'standard' in req.tiers and not _flag(technician, 'accepts_standard_service'):
        return False
    if 'premium' in req.tiers and not _flag(technician, 'accepts_premium_service'):
        return False
    return True


def _requirement_phrase(req: JobServiceRequirements) -> str:
    if 'one_time' in req.categories and 'amc' in req.categories:
        category = 'One-Time and AMC'
    elif 'amc' in req.categories:
        category = 'AMC'
    else:
        category = 'One-Time'
    if 'standard' in req.tiers and 'premium' in req.tiers:
        quality = ' Standard and Premium'
    elif 'standard' in req.tiers:
        quality = ' Standard'
    elif 'premium' in req.tiers:
        quality = ' Premium'
    else:
        quality = ''
    return f'{category}{quality}'.strip()


def _missing_flags(technician, req: JobServiceRequirements) -> list[str]:
    missing = []
    if 'one_time' in req.categories and not _flag(technician, 'accepts_one_time_jobs'):
        missing.append('One-Time Jobs')
    if 'amc' in req.categories and not _flag(technician, 'accepts_amc_jobs'):
        missing.append('AMC Jobs')
    if 'standard' in req.tiers and not _flag(technician, 'accepts_standard_service'):
        missing.append('Standard Service')
    if 'premium' in req.tiers and not _flag(technician, 'accepts_premium_service'):
        missing.append('Premium Service')
    return missing


def service_eligibility_error(technician, job) -> dict | None:
    """Structured 400 body when assignment or accept must be refused."""
    if technician is None or job is None:
        return None
    if technician_eligible_for_job(technician, job):
        return None
    req = job_service_requirements(job)
    missing = _missing_flags(technician, req)
    need = _requirement_phrase(req)
    missing_text = ', '.join(missing) if missing else 'this service type'
    name = getattr(technician, 'name', None) or 'This technician'
    return {
        'error': (
            f'{name} cannot take this {need} booking. '
            f'Enable {missing_text} on the technician profile.'
        ),
        'code': 'technician_service_ineligible',
        'technician_id': getattr(technician, 'id', None),
        'technician_name': getattr(technician, 'name', '') or '',
        'required_one_time': 'one_time' in req.categories,
        'required_amc': 'amc' in req.categories,
        'required_standard': 'standard' in req.tiers,
        'required_premium': 'premium' in req.tiers,
    }


def preview_job_for_eligibility(instance, data: dict | None):
    """Booking snapshot after a create/update payload, without saving."""
    values = {}
    if instance is not None:
        for field in _PREVIEW_FIELDS:
            values[field] = getattr(instance, field, None)
    for field in _PREVIEW_FIELDS:
        if data and field in data:
            values[field] = data[field]
    if not isinstance(values.get('service_items'), list):
        values['service_items'] = values.get('service_items') or []
    return SimpleNamespace(**values)
