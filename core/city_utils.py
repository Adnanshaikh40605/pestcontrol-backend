"""City label helpers for dashboard stats and booking create."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from django.db.models import CharField, Count, Value as V
from django.db.models.functions import Coalesce


def display_city_name(name: str | None) -> str:
    """Pretty display: 'mumbai' / 'Navi mumbai' → 'Mumbai' / 'Navi Mumbai'."""
    raw = (name or '').strip()
    if not raw:
        return ''
    return ' '.join(part.capitalize() for part in raw.split())


@lru_cache(maxsize=1)
def _master_city_lookup() -> dict[str, str]:
    """Map casefolded city name → canonical master City.name (display-normalized)."""
    from core.models import City

    mapping: dict[str, str] = {}
    for name in City.objects.values_list('name', flat=True):
        if not name:
            continue
        display = display_city_name(name)
        mapping[name.casefold()] = display
        mapping[display.casefold()] = display
    # Common aliases → master cities
    aliases = {
        'bombay': 'Mumbai',
        'navi-mumbai': 'Navi Mumbai',
        'navimumbai': 'Navi Mumbai',
        'new mumbai': 'Navi Mumbai',
        'lonavala': 'Lonavla',
        'lonawala': 'Lonavla',
    }
    for alias, target in aliases.items():
        # Prefer existing master display if present
        mapping[alias] = mapping.get(target.casefold(), target)
    return mapping


def clear_master_city_lookup_cache() -> None:
    _master_city_lookup.cache_clear()


def canonical_city_label(raw: str | None) -> str:
    """Resolve a free-text / master city string to one display label for grouping."""
    text = (raw or '').strip()
    if not text:
        return ''
    lookup = _master_city_lookup()
    hit = lookup.get(text.casefold())
    if hit:
        return hit
    return display_city_name(text)


def resolve_master_city(city_name: str | None):
    """Return City instance matching name/alias (case-insensitive), or None."""
    from core.models import City

    text = (city_name or '').strip()
    if not text:
        return None

    city = City.objects.filter(name__iexact=text).first()
    if city:
        return city

    # Alias → canonical display → master row
    canonical = canonical_city_label(text)
    if canonical and canonical.casefold() != text.casefold():
        city = City.objects.filter(name__iexact=canonical).first()
        if city:
            return city
        # Master may still be stored as 'Navi mumbai' / 'Lonavla'
        for name in City.objects.values_list('name', flat=True):
            if display_city_name(name).casefold() == canonical.casefold():
                return City.objects.filter(name=name).first()
    return None


def aggregate_city_counts(
    qs,
    *,
    limit: int = 12,
    distinct_booking: bool = False,
) -> list[dict]:
    """
    Group jobcards by city with case-insensitive merge and proper display names.

    Prefers master_city.name, falls back to free-text city.
    When distinct_booking=True, counts unique booking roots
    (Coalesce(parent_job_id, id)) so multi-service children don't inflate totals.
    """
    from django.db.models import F

    annotated = qs.annotate(
        city_label=Coalesce(
            'master_city__name',
            'city',
            V(''),
            output_field=CharField(),
        ),
        booking_root=Coalesce('parent_job_id', F('id')),
    ).exclude(city_label='')

    if distinct_booking:
        rows = annotated.values('city_label').annotate(
            count=Count('booking_root', distinct=True),
        )
    else:
        rows = annotated.values('city_label').annotate(count=Count('id'))

    # Skip country / plus-code noise that sometimes lands in free-text city.
    import re
    plus_code_re = re.compile(r'^[a-z0-9]{2,}\+[a-z0-9]+$', re.I)
    skip_labels = {'india', 'maharashtra', 'unknown', 'n/a', 'na', 'test'}

    merged: dict[str, dict] = {}
    for row in rows:
        display = canonical_city_label(row['city_label'])
        if not display:
            continue
        if display.casefold() in skip_labels:
            continue
        if plus_code_re.match(display.replace(' ', '')):
            continue
        key = display.casefold()
        if key in merged:
            merged[key]['count'] += row['count']
        else:
            merged[key] = {'city': display, 'count': row['count']}
    ordered = sorted(merged.values(), key=lambda item: (-item['count'], item['city']))
    return ordered[:limit]
