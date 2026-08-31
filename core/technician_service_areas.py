"""Technician ↔ City (service area) helpers for CRM assign and partner pool."""
from __future__ import annotations

import re
from typing import Iterable, Optional

from django.db.models import Count, Prefetch, Q, QuerySet

from core.city_utils import display_city_name, resolve_master_city
from core.models import City, JobCard, Technician


def _split_legacy_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r'[,/|]+', str(raw))
    return [p.strip() for p in parts if p and p.strip()]


def sync_legacy_city_labels(technician: Technician) -> None:
    """Keep legacy city/service_area CharFields in sync with M2M for older UIs."""
    names = list(
        technician.service_cities.filter(is_active=True)
        .order_by('name')
        .values_list('name', flat=True)
    )
    label = ', '.join(display_city_name(n) for n in names)
    update_fields: list[str] = []
    if (technician.city or '') != label:
        technician.city = label
        update_fields.append('city')
    if (technician.service_area or '') != label:
        technician.service_area = label
        update_fields.append('service_area')
    if update_fields:
        update_fields.append('updated_at')
        technician.save(update_fields=update_fields)


def set_technician_service_cities(
    technician: Technician,
    city_ids: Iterable[int],
) -> Technician:
    """Replace M2M cities, de-dupe ids, and sync legacy text fields."""
    ids: list[int] = []
    seen: set[int] = set()
    for raw in city_ids or []:
        try:
            cid = int(raw)
        except (TypeError, ValueError):
            continue
        if cid in seen:
            continue
        seen.add(cid)
        ids.append(cid)
    cities = list(City.objects.filter(id__in=ids, is_active=True))
    technician.service_cities.set(cities)
    sync_legacy_city_labels(technician)
    return technician


def migrate_legacy_service_areas_for_technician(technician: Technician) -> int:
    """
    Map free-text city/service_area onto City M2M.
    Returns number of cities linked. Skips techs that already have M2M rows.
    """
    if technician.service_cities.exists():
        return technician.service_cities.count()

    linked: list[City] = []
    seen: set[int] = set()
    for token in _split_legacy_tokens(technician.city) + _split_legacy_tokens(
        technician.service_area
    ):
        city = resolve_master_city(token)
        if city and city.id not in seen:
            seen.add(city.id)
            linked.append(city)
    if linked:
        technician.service_cities.set(linked)
        sync_legacy_city_labels(technician)
    return len(linked)


def job_service_city(job: JobCard) -> Optional[City]:
    """Canonical City for a booking (master_city preferred, legacy text fallback)."""
    if job.master_city_id:
        # Prefer already-select_related instance when present
        return getattr(job, 'master_city', None) or City.objects.filter(id=job.master_city_id).first()
    if job.city:
        return resolve_master_city(job.city)
    return None


def technician_serves_city(technician: Technician, city: Optional[City]) -> bool:
    """
    True when the technician may be assigned for this city.
    Empty M2M = legacy / unscoped — eligible for any city (desk can assign anyone active).
    Bookings with no city remain open to any active technician.
    """
    if city is None:
        return True
    # Use prefetched cache when available
    if hasattr(technician, '_prefetched_objects_cache') and 'service_cities' in getattr(
        technician, '_prefetched_objects_cache', {}
    ):
        cities = list(technician.service_cities.all())
    else:
        cities = list(technician.service_cities.all())
    if not cities:
        return True
    return any(c.id == city.id for c in cities)


def filter_technicians_for_city(
    qs: QuerySet[Technician],
    city: Optional[City],
) -> QuerySet[Technician]:
    """Filter by service city when set; always include techs with no service cities (legacy)."""
    if city is None:
        return qs
    return qs.annotate(
        _service_city_count=Count('service_cities', distinct=True),
    ).filter(
        Q(_service_city_count=0) | Q(service_cities=city),
    ).distinct()


def eligible_technicians_queryset(
    *,
    city: Optional[City] = None,
    city_id: Optional[int] = None,
    job: Optional[JobCard] = None,
    active_only: bool = True,
) -> QuerySet[Technician]:
    """Active technicians whose service_cities include the booking city (or unscoped)."""
    resolved = city
    if resolved is None and city_id:
        resolved = City.objects.filter(id=city_id, is_active=True).first()
    if resolved is None and job is not None:
        resolved = job_service_city(job)

    qs = Technician.objects.select_related('partner_account').annotate(
        active_jobs=Count('jobcards', filter=Q(jobcards__status__iexact='On Process'))
    )
    if active_only:
        qs = qs.filter(is_active=True)
    qs = qs.prefetch_related(
        Prefetch(
            'service_cities',
            queryset=City.objects.select_related('state').filter(is_active=True).order_by('name'),
        )
    ).order_by('name')
    return filter_technicians_for_city(qs, resolved)


def partner_service_city_ids(partner) -> set[int]:
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        return set()
    return set(tech.service_cities.values_list('id', flat=True))


def serialize_service_cities(technician: Technician) -> list[dict]:
    cities = list(technician.service_cities.all())
    cities = sorted(cities, key=lambda c: (c.name or '').lower())
    out = []
    for c in cities:
        if not c.is_active:
            continue
        state = getattr(c, 'state', None)
        out.append({
            'id': c.id,
            'name': display_city_name(c.name) or c.name,
            'is_active': c.is_active,
            'state': c.state_id,
            'state_name': getattr(state, 'name', None) if state else None,
        })
    return out
