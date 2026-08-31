"""Technician ↔ City (service area) helpers for CRM assign and partner pool."""
from __future__ import annotations

import re
from typing import Iterable, Optional

from django.db.models import Count, Prefetch, Q, QuerySet

from core.city_utils import canonical_city_label, display_city_name, resolve_master_city
from core.models import City, JobCard, Technician


def city_match_key(city: City | None) -> str:
    """Stable key for matching equivalent city rows (case / alias / display)."""
    if not city:
        return ''
    return canonical_city_label(city.name).casefold()


def equivalent_city_ids(city: City | None) -> list[int]:
    """All active City PKs that represent the same place as `city`."""
    if not city:
        return []
    key = city_match_key(city)
    if not key:
        return [city.id]
    ids: set[int] = {city.id}
    for row in City.objects.filter(is_active=True).only('id', 'name'):
        if city_match_key(row) == key:
            ids.add(row.id)
    return sorted(ids)


def canonical_city_record(city: City) -> City:
    """Pick one representative City row per logical city name."""
    key = city_match_key(city)
    if not key:
        return city
    rows = list(City.objects.filter(is_active=True).only('id', 'name'))
    matches = [row for row in rows if city_match_key(row) == key]
    if not matches:
        return city
    return min(matches, key=lambda row: row.id)


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
    raw_cities = list(City.objects.filter(id__in=ids, is_active=True))
    canonical: list[City] = []
    seen_keys: set[str] = set()
    for city in raw_cities:
        key = city_match_key(city)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        canonical.append(canonical_city_record(city))
    technician.service_cities.set(canonical)
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
        city = getattr(job, 'master_city', None) or City.objects.filter(id=job.master_city_id).first()
        if city:
            return canonical_city_record(city)
    location = getattr(job, 'master_location', None)
    if location is not None and getattr(location, 'city_id', None):
        loc_city = getattr(location, 'city', None)
        if loc_city is None:
            loc_city = City.objects.filter(id=location.city_id, is_active=True).first()
        if loc_city:
            return canonical_city_record(loc_city)
    if job.city:
        resolved = resolve_master_city(job.city)
        if resolved:
            return canonical_city_record(resolved)
    return None


def technician_service_cities_list(technician: Technician) -> list[City]:
    if hasattr(technician, '_prefetched_objects_cache') and 'service_cities' in getattr(
        technician, '_prefetched_objects_cache', {}
    ):
        return list(technician.service_cities.all())
    return list(technician.service_cities.all())


def technician_has_service_areas(technician: Technician) -> bool:
    return bool(technician_service_cities_list(technician))


def technician_serves_city(technician: Technician, city: Optional[City]) -> bool:
    """
    True when the technician may be assigned for this city.
    Bookings with no city remain open to any active technician.
    Technicians with no service areas cannot serve city-scoped bookings.
    """
    if city is None:
        return True
    cities = technician_service_cities_list(technician)
    if not cities:
        return False
    target_key = city_match_key(city)
    if not target_key:
        return any(c.id == city.id for c in cities)
    return any(city_match_key(c) == target_key for c in cities)


def assignment_service_area_error(
    technician: Technician,
    booking_city: Optional[City],
) -> Optional[dict]:
    """Structured assign error when service area rules block assignment."""
    if booking_city is None:
        return None

    cities = technician_service_cities_list(technician)
    city_label = display_city_name(booking_city.name) or booking_city.name

    if not cities:
        return {
            'error': (
                f'{technician.name} has no Service Areas selected. '
                f'Open Technicians → Edit and add at least one city (e.g. {city_label}) '
                f'before assigning this booking.'
            ),
            'code': 'technician_no_service_area',
            'technician_id': technician.id,
            'technician_name': technician.name,
            'service_city_id': booking_city.id,
            'service_city_name': city_label,
        }

    if not technician_serves_city(technician, booking_city):
        areas = ', '.join(
            display_city_name(c.name) or c.name for c in sorted(cities, key=lambda c: c.name.lower())
        )
        return {
            'error': (
                f'{technician.name} does not serve {city_label}. '
                f'Configured service areas: {areas}. '
                f'Add {city_label} on the technician profile to assign this booking.'
            ),
            'code': 'technician_outside_service_area',
            'technician_id': technician.id,
            'technician_name': technician.name,
            'service_city_id': booking_city.id,
            'service_city_name': city_label,
            'technician_service_areas': areas,
        }

    return None


def filter_technicians_for_city(
    qs: QuerySet[Technician],
    city: Optional[City],
) -> QuerySet[Technician]:
    """Filter by service city when set; exclude techs with no service areas."""
    if city is None:
        return qs
    match_ids = equivalent_city_ids(city)
    return qs.annotate(
        _service_city_count=Count('service_cities', distinct=True),
    ).filter(
        _service_city_count__gt=0,
        service_cities__id__in=match_ids,
    ).distinct()


def eligible_technicians_queryset(
    *,
    city: Optional[City] = None,
    city_id: Optional[int] = None,
    job: Optional[JobCard] = None,
    active_only: bool = True,
) -> QuerySet[Technician]:
    """Active technicians whose service_cities include the booking city."""
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
