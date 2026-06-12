"""Seed Pricing Master from legacy rate cards — insert only, never overwrite."""

from __future__ import annotations

from decimal import Decimal

from core.models import PricingPropertyCategory, PricingRegion, PricingRate

from .lonavala import LONAVALA_PRICING
from .mumbai import MUMBAI_PRICING

FOGGING_AREAS = {
    'Up to 1,000 Sq.Ft.',
    '1,001-2,000 Sq.Ft.',
    '2,001-5,000 Sq.Ft.',
    '5,001-10,000 Sq.Ft.',
}

VILLA_AREAS = {
    'Up to 1,000 Sq.Ft.',
    '1,001-2,000 Sq.Ft.',
    '2,001-4,000 Sq.Ft.',
    '4,001-6,000 Sq.Ft.',
    '6,001-10,000 Sq.Ft.',
}

RODENT_AREAS = {
    'Up to 1,000 Sq.Ft.',
    '1,001-2,000 Sq.Ft.',
    '2,001-4,000 Sq.Ft.',
    '4,001-6,000 Sq.Ft.',
    '6,001-10,000 Sq.Ft.',
    '10,001-15,000 Sq.Ft.',
    '15,001-20,000 Sq.Ft.',
    'Windows',
    'Society Area',
}


def infer_property_category(service_package: str, area_key: str) -> str:
    if area_key == 'Commercial Space':
        return PricingPropertyCategory.COMMERCIAL
    if area_key in ('Windows', 'Society Area'):
        return PricingPropertyCategory.RODENT
    if service_package == 'Mosquito' and area_key in FOGGING_AREAS:
        return PricingPropertyCategory.FOGGING
    if area_key in VILLA_AREAS and service_package == 'Cockroach / Ants':
        return PricingPropertyCategory.VILLA
    if area_key in RODENT_AREAS and service_package == 'Rodent':
        return PricingPropertyCategory.RODENT
    if 'Sq.Ft.' in area_key:
        if service_package == 'Rodent':
            return PricingPropertyCategory.RODENT
        if service_package == 'Mosquito':
            return PricingPropertyCategory.FOGGING
        return PricingPropertyCategory.VILLA
    return PricingPropertyCategory.RESIDENTIAL


def _seed_region(
    *,
    slug: str,
    name: str,
    pricing_table: dict,
    is_default: bool = False,
    city_name: str | None = None,
) -> tuple[int, int]:
    from core.models import City

    city = None
    if city_name:
        city = City.objects.filter(name__iexact=city_name).first()

    region, created = PricingRegion.objects.get_or_create(
        slug=slug,
        defaults={
            'name': name,
            'city': city,
            'is_default': is_default,
            'is_active': True,
        },
    )
    if city and region.city_id != city.id:
        region.city = city
        region.save(update_fields=['city', 'updated_at'])

    created = 0
    skipped = 0
    for service_package, plans in pricing_table.items():
        for plan_type, areas in plans.items():
            for area_key, amount in areas.items():
                _, was_created = PricingRate.objects.get_or_create(
                    region=region,
                    service_package=service_package,
                    plan_type=plan_type,
                    area_key=area_key,
                    defaults={
                        'amount': Decimal(str(amount)),
                        'property_category': infer_property_category(service_package, area_key),
                        'is_active': True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1
    return created, skipped


def seed_pricing_master() -> dict[str, dict[str, int]]:
    """Import legacy Mumbai + Lonavala rates. Existing rows are never updated."""
    mumbai_created, mumbai_skipped = _seed_region(
        slug='mumbai',
        name='Mumbai',
        pricing_table=MUMBAI_PRICING,
        is_default=True,
        city_name='Mumbai',
    )
    lonavala_created, lonavala_skipped = _seed_region(
        slug='lonavala',
        name='Lonavala',
        pricing_table=LONAVALA_PRICING,
        city_name='Lonavala',
    )
    return {
        'mumbai': {'created': mumbai_created, 'skipped': mumbai_skipped},
        'lonavala': {'created': lonavala_created, 'skipped': lonavala_skipped},
    }
