"""Service rate helpers — aligned with CRM Create Booking PRICING_DATA."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

# Mirrors pest crm/src/constants/pricing.ts (Create Booking)
PRICING_DATA: dict[str, dict[str, dict[str, int]]] = {
    'Cockroach / Ants': {
        'AMC 3 Services': {
            '1 RK': 1800,
            '1 BHK': 2200,
            '2 BHK': 2500,
            '3 BHK': 3000,
            '4 BHK': 3500,
        },
        'One Time Service': {
            '1 RK': 1000,
            '1 BHK': 1200,
            '2 BHK': 1500,
            '3 BHK': 1800,
            '4 BHK': 2000,
        },
    },
    'Bed Bugs': {
        'One Time Service': {
            '1 RK': 2000,
            '1 BHK': 2500,
            '2 BHK': 3000,
            '3 BHK': 3500,
            '4 BHK': 4000,
        },
    },
    'Termite': {
        'One Time Service': {
            '1 RK': 2000,
            '1 BHK': 2500,
            '2 BHK': 3000,
            '3 BHK': 3500,
            '4 BHK': 4000,
        },
    },
    'Rodent': {
        'One Time Service': {
            'Windows': 1000,
            'Society Area': 0,
        },
    },
    'Mosquito': {
        'One Time Service': {
            '1 RK': 800,
            '1 BHK': 1000,
            '2 BHK': 1500,
            '3 BHK': 1800,
            '4 BHK': 2000,
        },
    },
    'Hotel / Commercial': {
        'One Time Service': {
            'Commercial Space': 0,
        },
    },
}

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
}


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
        text = raw.strip().lower()
        if text in BHK_ALIASES:
            return BHK_ALIASES[text]
        match = re.search(r'(\d)\s*bhk', text, re.I)
        if match:
            key = f"{match.group(1)} bhk"
            return BHK_ALIASES.get(key, f"{match.group(1)} BHK")
        if text in ('windows', 'society area', 'commercial space'):
            return text.title() if text != 'society area' else 'Society Area'
    return None


def _match_packages(pest_type: str | None, pest_problems: str | None) -> list[str]:
    """Resolve pricing packages from pest text (deduped, order preserved)."""
    combined = f"{pest_type or ''} {pest_problems or ''}".lower()
    # Exact combined package names from Create Booking
    for pkg in PRICING_DATA:
        if pkg.lower() in combined:
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


def _package_rate(package: str, plan_key: str, area_key: str | None) -> int | None:
    service = PRICING_DATA.get(package)
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
    estimated_price: Decimal | int | float | None = None,
) -> dict[str, Any]:
    """
    Build rate breakdown for PLAN + RATE UI.
    Uses the same BHK matrix as Create Booking when size is known.
    """
    plan_key = _plan_label(service_frequency)
    plan_display = _display_plan(service_frequency)
    area_key = _normalize_bhk(premise_size, location, pest_type, pest_problems)
    packages = _match_packages(pest_type, pest_problems)

    items: list[dict[str, Any]] = []
    total = 0
    notes: list[str] = []

    for package in packages:
        rate = _package_rate(package, plan_key, area_key)
        if rate is None and area_key is None:
            notes.append(f'{package}: select BHK on booking')
            continue
        if rate is None:
            notes.append(f'{package}: rate N/A for {area_key}')
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
        if notes:
            result['rate_note'] = '; '.join(notes)
        return result

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
