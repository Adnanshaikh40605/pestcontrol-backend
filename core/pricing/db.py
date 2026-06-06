"""Load pricing from Pricing Master DB with hardcoded fallback."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .lonavala import (
    LONAVALA_MOSQUITO_FOGGING_LOCATIONS,
    LONAVALA_PRICING,
    LONAVALA_RESIDENTIAL_LOCATIONS,
    LONAVALA_RODENT_LOCATIONS,
    LONAVALA_SERVICE_TYPES,
    LONAVALA_VILLA_LOCATIONS,
)
from .mumbai import MUMBAI_PRICING, MUMBAI_PROPERTY_LOCATIONS, MUMBAI_SERVICE_TYPES

LONAVALA_CITY_NAMES = frozenset({'lonavala'})

HARDCODED_BY_REGION: dict[str, dict[str, dict[str, dict[str, int]]]] = {
    'mumbai': MUMBAI_PRICING,
    'lonavala': LONAVALA_PRICING,
}

HARDCODED_SERVICE_TYPES: dict[str, dict[str, list[str]]] = {
    'mumbai': MUMBAI_SERVICE_TYPES,
    'lonavala': LONAVALA_SERVICE_TYPES,
}

HARDCODED_RESIDENTIAL: dict[str, list[str]] = {
    'mumbai': MUMBAI_PROPERTY_LOCATIONS,
    'lonavala': LONAVALA_RESIDENTIAL_LOCATIONS,
}

HARDCODED_VILLA: dict[str, list[str]] = {
    'mumbai': [],
    'lonavala': LONAVALA_VILLA_LOCATIONS,
}

HARDCODED_RODENT: dict[str, list[str]] = {
    'mumbai': ['Society Area', 'Windows'],
    'lonavala': LONAVALA_RODENT_LOCATIONS,
}

HARDCODED_FOGGING: dict[str, list[str]] = {
    'mumbai': [],
    'lonavala': LONAVALA_MOSQUITO_FOGGING_LOCATIONS,
}


def normalize_city_name(city: str | None) -> str:
    return (city or '').strip()


def _resolve_region_slug_from_db(city: str | None) -> str | None:
    try:
        from core.models import PricingRegion

        name = normalize_city_name(city)
        if not name:
            return None

        region = (
            PricingRegion.objects.filter(is_active=True)
            .filter(city__name__iexact=name)
            .first()
        )
        if region:
            return region.slug

        region = PricingRegion.objects.filter(is_active=True, slug__iexact=name).first()
        if region:
            return region.slug
    except Exception:
        return None
    return None


def pricing_region_for_city(city: str | None) -> str:
    db_slug = _resolve_region_slug_from_db(city)
    if db_slug:
        return db_slug

    name = normalize_city_name(city).lower()
    if name in LONAVALA_CITY_NAMES:
        return 'lonavala'
    return 'mumbai'


def _rates_queryset(region_slug: str):
    from core.models import PricingRate

    return PricingRate.objects.filter(
        region__slug=region_slug,
        region__is_active=True,
        is_active=True,
    ).select_related('region')


def _build_pricing_table_from_db(region_slug: str) -> dict[str, dict[str, dict[str, int]]] | None:
    rates = list(_rates_queryset(region_slug))
    if not rates:
        return None

    table: dict[str, dict[str, dict[str, int]]] = {}
    for rate in rates:
        amount = int(Decimal(str(rate.amount)))
        table.setdefault(rate.service_package, {}).setdefault(rate.plan_type, {})[rate.area_key] = amount
    return table


def _areas_from_db(region_slug: str, category: str) -> list[str] | None:
    rates = _rates_queryset(region_slug).filter(property_category=category)
    areas = list(rates.values_list('area_key', flat=True).distinct())
    return areas or None


def get_pricing_data(city: str | None = None, region: str | None = None) -> dict[str, dict[str, dict[str, int]]]:
    resolved = region or pricing_region_for_city(city)
    db_table = _build_pricing_table_from_db(resolved)
    if db_table:
        return db_table
    return HARDCODED_BY_REGION.get(resolved, MUMBAI_PRICING)


def get_service_types(city: str | None = None, region: str | None = None) -> dict[str, list[str]]:
    resolved = region or pricing_region_for_city(city)
    table = get_pricing_data(region=resolved)
    if table:
        return {pkg: list(plans.keys()) for pkg, plans in table.items()}
    return HARDCODED_SERVICE_TYPES.get(resolved, MUMBAI_SERVICE_TYPES)


def _location_list(region_slug: str, category: str, hardcoded: list[str]) -> list[str]:
    db_areas = _areas_from_db(region_slug, category)
    return db_areas if db_areas else hardcoded


def get_area_options(
    *,
    city: str | None = None,
    region: str | None = None,
    commercial_type: str = 'home',
    selected_services: list[str] | None = None,
) -> list[str]:
    resolved = region or pricing_region_for_city(city)
    services = selected_services or []
    qs = _rates_queryset(resolved)

    if qs.exists():
        options: list[str] = []
        for service in services:
            service_qs = qs.filter(service_package=service)
            if commercial_type == 'villa':
                if service in ('Bed Bugs', 'Termite'):
                    service_qs = service_qs.filter(property_category='residential')
                elif service == 'Cockroach / Ants':
                    service_qs = service_qs.filter(property_category='villa')
                elif service == 'Mosquito':
                    service_qs = service_qs.filter(property_category__in=['fogging', 'residential'])
                elif service == 'Rodent':
                    service_qs = service_qs.filter(property_category='rodent')
            else:
                if service in ('Bed Bugs', 'Termite'):
                    service_qs = service_qs.filter(property_category='residential')
                elif service == 'Cockroach / Ants':
                    service_qs = service_qs.filter(property_category='residential')
                elif service == 'Mosquito':
                    service_qs = service_qs.filter(property_category='residential')
                elif service == 'Rodent':
                    service_qs = service_qs.filter(property_category='rodent')
                elif service == 'Hotel / Commercial':
                    service_qs = service_qs.filter(property_category='commercial')
            options.extend(service_qs.values_list('area_key', flat=True).distinct())
        return list(dict.fromkeys(options))

    residential_locs = HARDCODED_RESIDENTIAL.get(resolved, MUMBAI_PROPERTY_LOCATIONS)
    villa_locs = HARDCODED_VILLA.get(resolved, [])
    fogging_locs = HARDCODED_FOGGING.get(resolved, [])
    rodent_locs = HARDCODED_RODENT.get(resolved, ['Society Area', 'Windows'])

    options: list[str] = []
    if commercial_type == 'villa':
        if 'Cockroach / Ants' in services:
            options.extend(villa_locs)
        if 'Mosquito' in services:
            options.extend(fogging_locs)
        if 'Rodent' in services:
            options.extend(rodent_locs)
        if any(s in services for s in ('Bed Bugs', 'Termite')):
            options.extend(['1 BHK', '2 BHK', '3 BHK', '4 BHK', '5 BHK'])
    else:
        residential_svcs = [s for s in services if s not in ('Rodent', 'Hotel / Commercial')]
        if residential_svcs:
            if any(s in services for s in ('Bed Bugs', 'Termite')):
                options.extend(['1 BHK', '2 BHK', '3 BHK', '4 BHK', '5 BHK'])
            if any(s in services for s in ('Cockroach / Ants', 'Mosquito')):
                options.extend(residential_locs)
        if 'Rodent' in services:
            options.extend(rodent_locs)
        if 'Hotel / Commercial' in services:
            options.append('Commercial Space')

    return list(dict.fromkeys(options))


def build_pricing_config_payload(city: str | None = None) -> dict[str, Any]:
    region = pricing_region_for_city(city)
    return {
        'region': region,
        'city': normalize_city_name(city) or 'Mumbai',
        'pricing': get_pricing_data(region=region),
        'service_types': get_service_types(region=region),
        'residential_locations': _location_list(
            region, 'residential', HARDCODED_RESIDENTIAL.get(region, MUMBAI_PROPERTY_LOCATIONS),
        ),
        'villa_locations': _location_list(region, 'villa', HARDCODED_VILLA.get(region, [])),
        'rodent_locations': _location_list(
            region, 'rodent', HARDCODED_RODENT.get(region, ['Society Area', 'Windows']),
        ),
        'source': 'database' if _rates_queryset(region).exists() else 'legacy',
    }
