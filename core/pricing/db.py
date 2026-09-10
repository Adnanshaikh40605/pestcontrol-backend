"""Load pricing from Pricing Master DB with hardcoded fallback."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .aliases import (
    is_cockroach_family,
    packages_for_area_lookup,
)
from .lonavala import (
    LONAVALA_MOSQUITO_FOGGING_LOCATIONS,
    LONAVALA_PRICING,
    LONAVALA_RESIDENTIAL_LOCATIONS,
    LONAVALA_RODENT_LOCATIONS,
    LONAVALA_SERVICE_TYPES,
    LONAVALA_VILLA_LOCATIONS,
)
from .mumbai import MUMBAI_PRICING, MUMBAI_PROPERTY_LOCATIONS, MUMBAI_SERVICE_TYPES, COMMERCIAL_AREA_KEY

# Include common CRM master-data spellings (e.g. "Lonavla" vs "Lonavala").
LONAVALA_CITY_NAMES = frozenset({'lonavala', 'lonavla'})


def is_lonavala_city_name(city: str | None) -> bool:
    """True for Lonavala service cities, including known spelling variants."""
    if not city:
        return False
    normalized = ''.join(normalize_city_name(city).lower().split())
    if normalized in LONAVALA_CITY_NAMES:
        return True
    return normalized.startswith('lonaval')

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

COMMERCIAL_PROPERTY_TYPES = frozenset({'office', 'other', 'hotel', 'society'})


def _append_commercial_area_option(
    options: list[str],
    *,
    commercial_type: str,
    selected_services: list[str],
    region_slug: str | None = None,
) -> list[str]:
    """Add Commercial area only when a real PricingRate (or legacy card) has it."""
    if commercial_type not in COMMERCIAL_PROPERTY_TYPES:
        return options
    residential_svcs = [
        s for s in selected_services if s not in ('Rodent', 'Hotel / Commercial')
    ]
    if not residential_svcs:
        return options
    if COMMERCIAL_AREA_KEY in options:
        return options

    if region_slug:
        from .aliases import resolve_service_package

        live = set(
            _rates_queryset(region_slug).values_list('service_package', flat=True).distinct()
        )
        check_packages = [
            resolve_service_package(service, live) for service in residential_svcs
        ]
        has_row = _rates_queryset(region_slug).filter(
            service_package__in=check_packages,
            area_key=COMMERCIAL_AREA_KEY,
        ).exists()
        if not has_row:
            return options

    options.append(COMMERCIAL_AREA_KEY)
    return options


def normalize_city_name(city: str | None) -> str:
    return (city or '').strip()


def _resolve_region_slug_from_db(city: str | None) -> str | None:
    try:
        from core.models import PricingRegion

        name = normalize_city_name(city)
        if not name:
            return None

        if is_lonavala_city_name(name):
            region = PricingRegion.objects.filter(is_active=True, slug='lonavala').first()
            if region:
                return region.slug

        region = (
            PricingRegion.objects.filter(is_active=True)
            .filter(city__name__iexact=name)
            .first()
        )
        if region:
            return region.slug

        # Fuzzy match: Lonavla ↔ Lonavala
        if is_lonavala_city_name(name):
            region = (
                PricingRegion.objects.filter(is_active=True, city__name__icontains='lonaval')
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

    if is_lonavala_city_name(city):
        return 'lonavala'
    return 'mumbai'


def resolve_pricing_region_slug(
    city: str | None = None,
    *,
    master_city_id: int | None = None,
) -> str:
    """Resolve pricing region from master city id (preferred) or city name."""
    if master_city_id:
        try:
            from core.models import City, PricingRegion

            city_obj = City.objects.get(pk=int(master_city_id))
            region = (
                PricingRegion.objects.filter(is_active=True, city_id=city_obj.id)
                .order_by('slug')
                .first()
            )
            if region:
                return region.slug
            if is_lonavala_city_name(city_obj.name):
                region = PricingRegion.objects.filter(is_active=True, slug='lonavala').first()
                if region:
                    return region.slug
            city = city_obj.name
        except (City.DoesNotExist, ValueError, TypeError):
            pass

    return pricing_region_for_city(city)


# Add-ons, equipment and SLA charges are quotation line items priced per unit,
# visit or running foot. They belong in Pricing Master but must not reach the
# booking service dropdown, which would otherwise offer "Rodent cage" and
# "Night service surcharge" as bookable services.
NON_BOOKABLE_CATEGORIES = ('addon',)


def _rates_queryset(region_slug: str):
    from core.models import PricingRate

    return PricingRate.objects.filter(
        region__slug=region_slug,
        region__is_active=True,
        is_active=True,
    ).exclude(
        property_category__in=NON_BOOKABLE_CATEGORIES,
    ).select_related('region')


def _build_pricing_table_from_db(region_slug: str) -> dict[str, dict[str, dict[str, int]]] | None:
    rates = list(_rates_queryset(region_slug))
    if not rates:
        return None

    from core.pricing.gst import gst_breakdown

    # Customer-facing booking amount = total_with_gst (amount if inclusive).
    table: dict[str, dict[str, dict[str, int]]] = {}
    for rate in rates:
        breakdown = gst_breakdown(
            rate.amount,
            gst_percent=rate.gst_percent,
            price_includes_gst=rate.price_includes_gst,
        )
        amount = int(Decimal(str(breakdown['total_with_gst'])))
        table.setdefault(rate.service_package, {}).setdefault(rate.plan_type, {})[rate.area_key] = amount
    return table


def _build_rate_gst_from_db(region_slug: str) -> dict[str, dict[str, dict[str, dict[str, Any]]]] | None:
    """Nested GST metadata mirroring the pricing matrix for CRM booking UI."""
    rates = list(_rates_queryset(region_slug))
    if not rates:
        return None

    from core.pricing.gst import rate_gst_payload

    details: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for rate in rates:
        details.setdefault(rate.service_package, {}).setdefault(rate.plan_type, {})[
            rate.area_key
        ] = rate_gst_payload(rate)
    return details


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


def _service_area_queryset(qs, service: str, commercial_type: str):
    """Narrow rates for one selected service, honouring legacy name aliases."""
    packages = packages_for_area_lookup(service)
    service_qs = qs.filter(service_package__in=packages)
    lower = (service or '').casefold()
    cockroach = is_cockroach_family(service)
    bed_or_termite = (
        service in ('Bed Bugs', 'Termite', 'Termite Spot Treatment')
        or 'bed bug' in lower
        or 'termite' in lower
    )
    mosquito = service == 'Mosquito' or 'mosquito' in lower or 'fogging' in lower
    rodent = service == 'Rodent' or 'rodent' in lower
    hotel_commercial = service == 'Hotel / Commercial'

    if commercial_type == 'villa':
        if bed_or_termite:
            return service_qs.filter(property_category='residential')
        if cockroach:
            return service_qs.filter(property_category__in=['villa', 'residential'])
        if mosquito:
            return service_qs.filter(property_category__in=['fogging', 'residential'])
        if rodent:
            return service_qs.filter(property_category__in=['rodent', 'residential'])
        return service_qs

    if bed_or_termite:
        # Home bookings only see BHK sizes. Other property types keep hotel /
        # hospital ward rates from the 2026 chart.
        if commercial_type == 'home':
            return service_qs.filter(property_category='residential')
        return service_qs

    if cockroach:
        if commercial_type == 'home':
            return service_qs.filter(property_category='residential')
        if commercial_type == 'hotel':
            return service_qs.filter(property_category='hotel')
        if commercial_type == 'office':
            return service_qs.filter(property_category__in=['corporate', 'corporate_monthly'])
        if commercial_type == 'society':
            return service_qs.filter(property_category='society')
        # other / unknown commercial: chart commercial segments only (no BHK).
        return service_qs.filter(
            property_category__in=['hotel', 'corporate', 'corporate_monthly', 'commercial', 'hospital'],
        )

    if mosquito:
        if commercial_type == 'home':
            return service_qs.filter(property_category='residential')
        return service_qs.filter(
            property_category__in=['residential', 'fogging', 'commercial'],
        )

    if rodent:
        if commercial_type == 'home':
            return service_qs.filter(property_category__in=['rodent', 'residential'])
        return service_qs.filter(
            property_category__in=['rodent', 'residential', 'commercial'],
        )

    if hotel_commercial:
        return service_qs.filter(property_category='commercial')

    return service_qs


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
            service_qs = _service_area_queryset(qs, service, commercial_type)
            options.extend(service_qs.values_list('area_key', flat=True).distinct())
        return list(dict.fromkeys(_append_commercial_area_option(
            options,
            commercial_type=commercial_type,
            selected_services=services,
            region_slug=resolved,
        )))

    residential_locs = HARDCODED_RESIDENTIAL.get(resolved, MUMBAI_PROPERTY_LOCATIONS)
    villa_locs = HARDCODED_VILLA.get(resolved, [])
    fogging_locs = HARDCODED_FOGGING.get(resolved, [])
    rodent_locs = HARDCODED_RODENT.get(resolved, ['Society Area', 'Windows'])

    options: list[str] = []
    has_cockroach = any(is_cockroach_family(s) for s in services)
    has_mosquito = any(
        s == 'Mosquito' or 'mosquito' in s.casefold() for s in services
    )
    has_rodent = any(s == 'Rodent' or 'rodent' in s.casefold() for s in services)
    has_bed_or_termite = any(
        s in ('Bed Bugs', 'Termite', 'Termite Spot Treatment')
        or 'bed bug' in s.casefold()
        or 'termite' in s.casefold()
        for s in services
    )

    if commercial_type == 'villa':
        if has_cockroach:
            options.extend(villa_locs)
        if has_mosquito:
            options.extend(fogging_locs)
        if has_rodent:
            options.extend(rodent_locs)
        if has_bed_or_termite:
            options.extend(['1 BHK', '2 BHK', '3 BHK', '4 BHK', '5 BHK'])
    else:
        residential_svcs = [s for s in services if s not in ('Rodent', 'Hotel / Commercial')]
        if residential_svcs:
            if has_bed_or_termite:
                options.extend(['1 BHK', '2 BHK', '3 BHK', '4 BHK', '5 BHK'])
            if has_cockroach or has_mosquito:
                options.extend(residential_locs)
        if has_rodent:
            options.extend(rodent_locs)
        if 'Hotel / Commercial' in services:
            options.append('Commercial Space')

    return list(dict.fromkeys(_append_commercial_area_option(
        options,
        commercial_type=commercial_type,
        selected_services=services,
    )))


def build_pricing_config_payload(
    city: str | None = None,
    *,
    master_city_id: int | None = None,
) -> dict[str, Any]:
    region = resolve_pricing_region_slug(city, master_city_id=master_city_id)
    resolved_city = normalize_city_name(city)
    if not resolved_city and master_city_id:
        try:
            from core.models import City

            resolved_city = City.objects.filter(pk=int(master_city_id)).values_list('name', flat=True).first()
        except (ValueError, TypeError):
            resolved_city = None
    return {
        'region': region,
        'city': resolved_city or 'Mumbai',
        'pricing': get_pricing_data(region=region),
        'service_types': get_service_types(region=region),
        'residential_locations': _location_list(
            region, 'residential', HARDCODED_RESIDENTIAL.get(region, MUMBAI_PROPERTY_LOCATIONS),
        ),
        'villa_locations': _location_list(region, 'villa', HARDCODED_VILLA.get(region, [])),
        'rodent_locations': _location_list(
            region, 'rodent', HARDCODED_RODENT.get(region, ['Society Area', 'Windows']),
        ),
        'rate_gst': _build_rate_gst_from_db(region) or {},
        'source': 'database' if _rates_queryset(region).exists() else 'legacy',
    }
