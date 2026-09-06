"""Technician base services (pest types they are qualified to handle).

Stored on Technician.skills as a JSON list of canonical service names.
Exposed on the API as ``base_services``.
"""
from __future__ import annotations

import re
from typing import Iterable

from core.models import JobCard, Technician

# Canonical pest services for technician qualification (not property categories).
# Hotel / Commercial is a pricing category, not a base service — never include it.
CANONICAL_BASE_SERVICES: tuple[str, ...] = (
    'Cockroach / Ants',
    'Bed Bugs',
    'Termite',
    'Rodent',
    'Mosquito',
)

_CANONICAL_LOOKUP = {name.casefold(): name for name in CANONICAL_BASE_SERVICES}

# Property / booking categories that must not appear as base services.
_IGNORED_CATEGORY_KEYS: frozenset[str] = frozenset(
    {
        'hotel',
        'commercial',
        'hotel / commercial',
        'hotel/commercial',
        'commercial space',
    }
)

# Loose aliases staff / legacy data may use.
_SERVICE_ALIASES: dict[str, str] = {
    'cockroach': 'Cockroach / Ants',
    'cockroach / ants': 'Cockroach / Ants',
    'cockroach/ants': 'Cockroach / Ants',
    'ants': 'Cockroach / Ants',
    'general pest': 'Cockroach / Ants',
    'general pest control': 'Cockroach / Ants',
    'bed bug': 'Bed Bugs',
    'bed bugs': 'Bed Bugs',
    'bedbug': 'Bed Bugs',
    'bedbugs': 'Bed Bugs',
    'termite': 'Termite',
    'termite control': 'Termite',
    'rodent': 'Rodent',
    'rodents': 'Rodent',
    'rat': 'Rodent',
    'rats': 'Rodent',
    'mosquito': 'Mosquito',
    'mosquitoes': 'Mosquito',
}


def _norm_key(raw: str) -> str:
    text = re.sub(r'\s+', ' ', (raw or '').strip()).casefold()
    text = text.replace('／', '/')
    return text


def is_ignored_category_label(raw: str | None) -> bool:
    """True for property categories (e.g. Hotel / Commercial) — not pest services."""
    if not raw:
        return False
    return _norm_key(str(raw)) in _IGNORED_CATEGORY_KEYS


def canonicalize_service_name(raw: str | None) -> str | None:
    """Map a free-text service label to a canonical base-service name."""
    if not raw:
        return None
    key = _norm_key(str(raw))
    if not key:
        return None
    if key in _IGNORED_CATEGORY_KEYS:
        return None
    if key in _CANONICAL_LOOKUP:
        return _CANONICAL_LOOKUP[key]
    if key in _SERVICE_ALIASES:
        return _SERVICE_ALIASES[key]
    # Substring fallback (e.g. "Termite Treatment - Pre Construction")
    for alias, canonical in _SERVICE_ALIASES.items():
        if alias in key or key in alias:
            return canonical
    for canonical in CANONICAL_BASE_SERVICES:
        if canonical.casefold() in key or key in canonical.casefold():
            return canonical
    return None


def normalize_base_services(values: Iterable[str] | None) -> list[str]:
    """De-dupe and canonicalize a list of service names; drop unknowns/categories."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        if is_ignored_category_label(str(raw)):
            continue
        canon = canonicalize_service_name(str(raw))
        if not canon or canon in seen:
            continue
        seen.add(canon)
        out.append(canon)
    # Stable order matching the product checklist
    return [name for name in CANONICAL_BASE_SERVICES if name in seen]


def default_base_services() -> list[str]:
    """All pest services selected — default until staff narrows qualifications."""
    return list(CANONICAL_BASE_SERVICES)


def get_technician_base_services(technician: Technician | None) -> list[str]:
    if technician is None:
        return []
    return normalize_base_services(getattr(technician, 'skills', None) or [])


def set_technician_base_services(
    technician: Technician,
    services: Iterable[str] | None,
) -> Technician:
    """Persist selected base services onto Technician.skills."""
    normalized = normalize_base_services(services)
    if list(getattr(technician, 'skills', None) or []) != normalized:
        technician.skills = normalized
        technician.save(update_fields=['skills', 'updated_at'])
    return technician


def split_service_type_blob(raw: str | None) -> list[str]:
    """Split comma-joined service_type into parts."""
    if not raw:
        return []
    return [p.strip() for p in re.split(r'[,|]+', str(raw)) if p and p.strip()]


def job_service_names(job: JobCard) -> set[str]:
    """Canonical service names present on a booking (items, source, or type)."""
    names: set[str] = set()

    source = getattr(job, 'source_service', None)
    if source:
        canon = canonicalize_service_name(source)
        if canon:
            names.add(canon)

    items = list(getattr(job, 'service_items', None) or [])
    for item in items:
        canon = canonicalize_service_name((item or {}).get('service'))
        if canon:
            names.add(canon)

    if not names:
        for part in split_service_type_blob(getattr(job, 'service_type', None)):
            canon = canonicalize_service_name(part)
            if canon:
                names.add(canon)

    return names


def job_matches_technician_base_services(
    job: JobCard,
    technician: Technician | None,
) -> bool:
    """
    True when the technician may see/handle this booking by base services.

    Rules:
    - Empty base_services → allow all (legacy / not yet configured).
    - Otherwise require overlap between job services and technician services.
    - Jobs with no recognizable service label stay visible (unscoped).
    """
    allowed = get_technician_base_services(technician)
    if not allowed:
        return True
    job_names = job_service_names(job)
    if not job_names:
        return True
    return bool(job_names & set(allowed))


def job_matches_partner_base_services(job: JobCard, partner) -> bool:
    tech = getattr(partner, 'core_technician', None)
    return job_matches_technician_base_services(job, tech)
