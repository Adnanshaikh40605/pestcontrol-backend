"""Match website / customer-app pest selections to PricingRate rows.

Mirrors pestcontroll99/src/utils/catalogPricing.ts so UI quotes and JobCard
amounts stay aligned. Residential home bookings never fall back to addon,
society, hospital, hotel, corporate, or Integrated IPM rates.
"""

from __future__ import annotations

import re
from typing import Iterable

from core.models import PricingRate

# Website pest slug → keywords against service_package (word-boundary match).
PEST_MATCH_KEYS: dict[str, tuple[str, ...]] = {
    'cockroach-ants': ('cockroach', 'ant'),
    'mosquito': ('mosquito',),
    'termite': ('termite',),
    'rodent': ('rodent', 'rat'),
    'bedbugs': ('bed bug', 'bedbug', 'bed bugs'),
    'honey-bee': ('bee', 'wasp'),
    'wood-borer': ('wood borer', 'woodborer', 'borer'),
    'house-fly': ('house fly', 'housefly', 'fly control', 'flies', 'fly'),
    'hotel-commercial': ('general', 'commercial'),
    'other': ('general pest', 'general'),
}

PEST_PREFERRED_PACKAGES: dict[str, dict[str, tuple[str, ...]]] = {
    'cockroach-ants': {
        'standard': ('Cockroach Standard', 'Cockroach / Ants'),
        'premium': ('Cockroach Premium', 'Cockroach Standard', 'Cockroach / Ants'),
    },
    'rodent': {
        'standard': ('Regular Rodent', 'Rodent'),
        'premium': ('Kill-Rodent System', 'Regular Rodent', 'Rodent'),
    },
    'mosquito': {
        'standard': ('Mosquito Cold Fogging', 'Mosquito'),
        'premium': ('Mosquito Thermal Fogging', 'Mosquito Cold Fogging', 'Mosquito'),
    },
    'termite': {
        'standard': ('Termite Spot Treatment', 'Termite'),
        'premium': ('Termite Spot Treatment', 'Termite'),
    },
    'bedbugs': {
        'standard': ('Bed Bugs',),
        'premium': ('Bed Bugs',),
    },
}

# service_type labels from the website → pest slug
SERVICE_LABEL_TO_PEST: dict[str, str] = {
    'cockroach control, ant control': 'cockroach-ants',
    'cockroach control': 'cockroach-ants',
    'ant control': 'cockroach-ants',
    'mosquito control': 'mosquito',
    'termite control': 'termite',
    'rodent / rat control': 'rodent',
    'rodent control': 'rodent',
    'bed bug control': 'bedbugs',
    'honey bee / wasp removal': 'honey-bee',
    'wood borer control': 'wood-borer',
    'fly control': 'house-fly',
    'general pest control': 'other',
}

NON_HOME_CATEGORIES = frozenset({
    'addon',
    'society',
    'hotel',
    'hospital',
    'corporate',
    'commercial',
    'chain',
})

_AREA_FROM_BHK = {
    'room': 'Room / Chawl',
    '1rk': '1 RK',
    '1bhk': '1 BHK',
    '2bhk': '2 BHK',
    '3bhk': '3 BHK',
    '4bhk': '4 BHK',
    '5bhk': '5 BHK',
    '6bhk': '6 BHK',
    'other': 'Other',
}


def package_token_matches(keys: Iterable[str], service_package: str) -> bool:
    """Word-boundary match so ``rat`` does not hit ``Integrated``."""
    pkg = service_package or ''
    for key in keys:
        k = (key or '').strip().lower()
        if not k:
            continue
        escaped = re.escape(k).replace(r'\ ', r'\s+')
        pattern = rf'(^|[^a-z0-9]){escaped}([^a-z0-9]|$)'
        if re.search(pattern, pkg, flags=re.IGNORECASE):
            return True
    return False


def is_home_excluded_rate(rate: PricingRate) -> bool:
    cat = (rate.property_category or '').lower().strip()
    if cat in NON_HOME_CATEGORIES:
        return True
    pkg = (rate.service_package or '').lower()
    if 'integrated ipm' in pkg:
        return True
    if 'fly catcher' in pkg:
        return True
    if 'add-on' in pkg or 'addon' in pkg:
        return True
    if re.search(r'\bsociety\b', pkg):
        return True
    if 'servicing' in pkg and 'fly' in pkg:
        return True
    return False


def is_home_property(property_type: str | None, commercial_type: str | None = None) -> bool:
    prop = (property_type or '').lower()
    commercial = (commercial_type or '').lower()
    if commercial and commercial not in ('home', ''):
        return False
    if 'commercial' in prop or 'society' in prop or 'hotel' in prop or 'office' in prop:
        return False
    return True


def pest_slug_from_service_type(service_type: str) -> str | None:
    label = (service_type or '').strip().lower()
    if not label:
        return None
    if label in SERVICE_LABEL_TO_PEST:
        return SERVICE_LABEL_TO_PEST[label]
    # Multi-service labels: use the first known segment.
    for part in re.split(r'[,/|]+', label):
        part = part.strip()
        if part in SERVICE_LABEL_TO_PEST:
            return SERVICE_LABEL_TO_PEST[part]
    for key, slug in SERVICE_LABEL_TO_PEST.items():
        if key in label:
            return slug
    # Keyword fallback
    if 'rodent' in label or re.search(r'\brat\b', label):
        return 'rodent'
    if 'fly' in label:
        return 'house-fly'
    if 'cockroach' in label or re.search(r'\bant\b', label):
        return 'cockroach-ants'
    if 'general' in label:
        return 'other'
    if 'mosquito' in label:
        return 'mosquito'
    if 'termite' in label:
        return 'termite'
    return None


def _plan_matches(rate: PricingRate, is_amc: bool) -> bool:
    plan = (rate.plan_type or '').lower()
    amc = 'amc' in plan
    return amc if is_amc else not amc


def _prefer_named_packages(
    pool: list[PricingRate],
    pest_slug: str,
    treatment_quality: str,
) -> list[PricingRate]:
    prefs = PEST_PREFERRED_PACKAGES.get(pest_slug)
    if not prefs or not pool:
        return pool
    quality = 'premium' if treatment_quality == 'premium' else 'standard'
    names = prefs.get(quality) or prefs.get('standard') or ()
    for name in names:
        hits = [r for r in pool if (r.service_package or '').lower() == name.lower()]
        if hits:
            return hits
    return pool


def match_rate_for_pest(
    rates: Iterable[PricingRate],
    pest_slug: str,
    *,
    is_amc: bool,
    premise_type: str = 'residential',
    premise_size: str = '',
    treatment_quality: str = 'standard',
) -> PricingRate | None:
    keys = PEST_MATCH_KEYS.get(pest_slug)
    rate_list = list(rates)
    if not keys or not rate_list:
        return None

    is_home = premise_type != 'commercial'
    area = (premise_size or '').strip().lower()
    if area in _AREA_FROM_BHK:
        area = _AREA_FROM_BHK[area].lower()

    candidates = [r for r in rate_list if package_token_matches(keys, r.service_package)]
    if not candidates:
        return None

    if is_home:
        candidates = [r for r in candidates if not is_home_excluded_rate(r)]
        if not candidates:
            return None

    by_plan = [r for r in candidates if _plan_matches(r, is_amc)]
    pool = by_plan or candidates

    quality = (treatment_quality or 'standard').lower()
    quality_hits = [r for r in pool if quality in (r.service_package or '').lower()]
    if quality_hits:
        pool = quality_hits
    elif quality == 'standard':
        non_premium = [
            r for r in pool if 'premium' not in (r.service_package or '').lower()
        ]
        if non_premium:
            pool = non_premium

    pool = _prefer_named_packages(pool, pest_slug, quality)

    if area:
        exact = [r for r in pool if (r.area_key or '').lower() == area]
        if exact:
            return exact[0]
        soft = [
            r
            for r in pool
            if area in (r.area_key or '').lower() or (r.area_key or '').lower() in area
        ]
        if soft:
            return soft[0]
        # Explicit size requested but no catalog row — do not price a different BHK/RK.
        # Mirrors pestcontroll99 catalogPricing.ts / customer app catalog_pricing.dart.
        if is_home:
            return None

    if is_home:
        residential = []
        for r in pool:
            cat = (r.property_category or '').lower()
            key = (r.area_key or '').lower()
            if 'residential' in cat or 'bhk' in key or 'rk' in key:
                residential.append(r)
        if residential:
            return residential[0]
        return None

    commercial = []
    for r in pool:
        cat = (r.property_category or '').lower()
        key = (r.area_key or '').lower()
        if 'commercial' in cat or key == 'commercial':
            commercial.append(r)
    if commercial:
        return commercial[0]
    return pool[0] if pool else None


def sanitize_home_booking_rate(
    rate: PricingRate | None,
    *,
    service_type: str,
    bhk_size: str,
    booking_type: str,
    package_tier: str,
    property_type: str,
    region_id: int | None = None,
) -> tuple[PricingRate | None, bool]:
    """Return (rate_or_none, force_price_pending).

    Drops addon / society / Integrated IPM etc. for home bookings. When the
    supplied rate is unsuitable, tries a residential rematch from service_type.
    """
    if not is_home_property(property_type):
        return rate, False

    if rate is not None and not is_home_excluded_rate(rate):
        cat = (rate.property_category or '').lower()
        key = (rate.area_key or '').lower()
        if 'residential' in cat or 'bhk' in key or 'rk' in key or not cat:
            return rate, False

    pest = pest_slug_from_service_type(service_type)
    if not pest:
        return None, True

    qs = PricingRate.objects.filter(is_active=True)
    if region_id:
        qs = qs.filter(region_id=region_id)
    elif rate is not None:
        qs = qs.filter(region_id=rate.region_id)

    is_amc = (booking_type or '').lower() == 'amc'
    rematched = match_rate_for_pest(
        qs,
        pest,
        is_amc=is_amc,
        premise_type='residential',
        premise_size=bhk_size or '',
        treatment_quality=package_tier or 'standard',
    )
    if rematched is None:
        return None, True
    return rematched, False
