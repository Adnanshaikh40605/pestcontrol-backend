"""Service rate helpers — city-aware pricing aligned with CRM Create Booking."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from core.pricing import get_pricing_data
from core.pricing.mumbai import MUMBAI_PRICING

# Backward-compatible default (Mumbai)
PRICING_DATA = MUMBAI_PRICING

# Map free-text pests to pricing packages (same as Create Booking checkboxes)
PEST_TO_PACKAGE: list[tuple[str, str]] = [
    ('cockroach', 'Cockroach / Ants'),
    ('ants', 'Cockroach / Ants'),
    ('bed bug', 'Bed Bugs'),
    ('bed bugs', 'Bed Bugs'),
    ('termite', 'Termite'),
    ('rodent', 'Rodent'),
    ('mosquito', 'Mosquito'),
    ('hotel', 'Hotel / Commercial'),
    ('commercial', 'Hotel / Commercial'),
]

BHK_ALIASES = {
    '1 rk': '1 RK',
    '1rk': '1 RK',
    '1 bhk': '1 BHK',
    '1bhk': '1 BHK',
    '2 bhk': '2 BHK',
    '2bhk': '2 BHK',
    '3 bhk': '3 BHK',
    '3bhk': '3 BHK',
    '4 bhk': '4 BHK',
    '4bhk': '4 BHK',
    '5 bhk': '5 BHK',
    '5bhk': '5 BHK',
    '6 bhk': '6 BHK',
    '6bhk': '6 BHK',
    '7 bhk': '7 BHK',
    '7bhk': '7 BHK',
    '8 bhk': '8 BHK',
    '8bhk': '8 BHK',
    '9 bhk': '9 BHK',
    '9bhk': '9 BHK',
    '10 bhk': '10 BHK',
    '10bhk': '10 BHK',
}

SQFT_AREA_KEYS = [
    'Up to 1,000 Sq.Ft.',
    '1,001-2,000 Sq.Ft.',
    '2,001-4,000 Sq.Ft.',
    '2,001-5,000 Sq.Ft.',
    '4,001-6,000 Sq.Ft.',
    '5,001-10,000 Sq.Ft.',
    '6,001-10,000 Sq.Ft.',
    '10,001-15,000 Sq.Ft.',
    '15,001-20,000 Sq.Ft.',
]


def _plan_label(service_frequency: str | None) -> str:
    plan = (service_frequency or 'one-time').strip().lower()
    if plan in ('amc', 'annual', 'annual maintenance contract'):
        return 'AMC 3 Services'
    return 'One Time Service'


def _display_plan(service_frequency: str | None) -> str:
    plan = (service_frequency or 'one-time').strip().lower()
    return 'AMC' if plan in ('amc', 'annual', 'annual maintenance contract') else 'ONE TIME'


def _normalize_bhk(premise_size: str | None, *extra_sources: str | None) -> str | None:
    for raw in (premise_size, *extra_sources):
        if not raw:
            continue
        stripped = raw.strip()
        if stripped in SQFT_AREA_KEYS:
            return stripped
        text = stripped.lower()
        if text in BHK_ALIASES:
            return BHK_ALIASES[text]
        match = re.search(r'(\d{1,2})\s*bhk', text, re.I)
        if match:
            key = f"{match.group(1)} bhk"
            return BHK_ALIASES.get(key, f"{match.group(1)} BHK")
        if text in ('windows', 'society area', 'commercial space', 'commercial'):
            if text == 'commercial':
                return 'Commercial'
            return text.title() if text != 'society area' else 'Society Area'
    return None


def _parse_quoted_amount(*sources: str | None) -> int | None:
    """Extract a quoted rupee amount from staff remarks (e.g. '2500 bole hai')."""
    for raw in sources:
        if not raw:
            continue
        for match in re.finditer(r'(?:₹|rs\.?|inr)?\s*(\d{3,5})\b', raw, re.I):
            amount = int(match.group(1))
            if 500 <= amount <= 500000:
                return amount
    return None


def _match_packages(pest_type: str | None, pest_problems: str | None) -> list[str]:
    """Resolve pricing packages from pest text (deduped, order preserved)."""
    combined = f"{pest_type or ''} {pest_problems or ''}".lower()
    combined_slash = re.sub(r'\s*,\s*', ' / ', combined)
    # Exact combined package names from Create Booking
    for pkg in get_pricing_data():
        key = pkg.lower()
        if key in combined or key in combined_slash:
            return [pkg]

    found: list[str] = []
    seen: set[str] = set()
    for needle, package in PEST_TO_PACKAGE:
        if needle in combined and package not in seen:
            # Cockroach + ants → single package, not two lines
            if package == 'Cockroach / Ants' and 'Cockroach / Ants' in seen:
                continue
            found.append(package)
            seen.add(package)

    # "Cockroach, Ants" or cockroach-ants → one package
    if ('cockroach' in combined and 'ants' in combined) or 'cockroach-ants' in combined:
        if 'Cockroach / Ants' not in seen:
            return ['Cockroach / Ants']
        return ['Cockroach / Ants']

    return found


def _default_bhk_for_package(package: str) -> str | None:
    """When BHK unknown, use 2 BHK for standard residential packages."""
    if package in ('Rodent', 'Hotel / Commercial'):
        return None
    return '2 BHK'


def _package_rate(
    package: str,
    plan_key: str,
    area_key: str | None,
    pricing_table: dict[str, dict[str, dict[str, int]]] | None = None,
) -> int | None:
    table = pricing_table or PRICING_DATA
    service = table.get(package)
    if not service:
        return None
    type_data = service.get(plan_key)
    if not type_data:
        # Fall back to one-time if AMC not defined for package
        type_data = service.get('One Time Service')
    if not type_data:
        return None
    if not area_key:
        return None
    if area_key in type_data:
        return type_data[area_key]
    return None


def compute_service_rate_info(
    *,
    pest_type: str | None = None,
    pest_problems: str | None = None,
    service_frequency: str | None = None,
    premise_size: str | None = None,
    location: str | None = None,
    service_city: str | None = None,
    remark: str | None = None,
    estimated_price: Decimal | int | float | None = None,
) -> dict[str, Any]:
    """
    Build rate breakdown for PLAN + RATE UI.
    Uses the same BHK matrix as Create Booking when size is known.
    """
    plan_key = _plan_label(service_frequency)
    plan_display = _display_plan(service_frequency)
    city_for_pricing = service_city or location
    pricing_table = get_pricing_data(city_for_pricing)
    area_key = _normalize_bhk(
        premise_size, location, pest_type, pest_problems, remark,
    )
    packages = _match_packages(pest_type, pest_problems)
    quoted_from_remark = _parse_quoted_amount(remark, pest_type, location)

    items: list[dict[str, Any]] = []
    total = 0
    notes: list[str] = []
    used_estimate_bhk = False

    effective_area = area_key
    if not effective_area and packages:
        fallback = _default_bhk_for_package(packages[0])
        if fallback:
            effective_area = fallback
            used_estimate_bhk = True

    for package in packages:
        rate = _package_rate(package, plan_key, effective_area, pricing_table)
        if rate is None:
            notes.append(f'{package}: rate N/A for {effective_area or "size"}')
            continue
        if rate == 0:
            notes.append(f'{package}: inspection / visit quote')
            continue
        items.append({'pest': package, 'rate': rate})
        total += rate

    if items:
        result: dict[str, Any] = {
            'plan': plan_display,
            'items': items,
            'total': total,
            'display_total': total,
            'rate_label': 'Service Rate',
            'has_service_rate': True,
        }
        if area_key:
            result['area_label'] = area_key
        elif used_estimate_bhk and effective_area:
            result['area_label'] = f'{effective_area} (est.)'
            notes.insert(0, 'Confirm BHK on booking for exact price')
        if notes:
            result['rate_note'] = '; '.join(notes)
        return result

    if quoted_from_remark is not None:
        return {
            'plan': plan_display,
            'items': [],
            'total': quoted_from_remark,
            'display_total': quoted_from_remark,
            'rate_label': 'Quoted (remark)',
            'has_service_rate': False,
            'area_label': area_key,
        }

    if estimated_price is not None:
        try:
            amount = int(Decimal(str(estimated_price)))
        except Exception:
            amount = None
        if amount is not None and amount > 0:
            return {
                'plan': plan_display,
                'items': [],
                'total': amount,
                'display_total': amount,
                'rate_label': 'Quoted Price',
                'has_service_rate': False,
                'area_label': area_key,
            }

    return {
        'plan': plan_display,
        'items': [],
        'total': None,
        'display_total': None,
        'rate_label': None,
        'has_service_rate': False,
        'area_label': area_key,
    }
