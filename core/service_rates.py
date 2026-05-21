"""Service rate helpers for CRM and website lead displays."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

PEST_SERVICE_RATES: dict[str, int] = {
    'cockroach': 1200,
    'termite': 3000,
    'rodent': 1800,
}

PEST_ALIASES: dict[str, str] = {
    'bed bug': 'bed bugs',
    'bed bugs': 'bed bugs',
    'wood borer': 'termite',
}


def _normalize_pest_key(name: str) -> str:
    key = (name or '').strip().lower()
    return PEST_ALIASES.get(key, key)


def parse_pest_names(*sources: str | None) -> list[str]:
    """Extract known pest labels from free-text or single pest fields."""
    found: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if not source:
            continue
        text = source.replace('\n', ',')
        for part in re.split(r'[,;/|]+', text):
            cleaned = part.strip()
            if not cleaned:
                continue
            key = _normalize_pest_key(cleaned)
            for pest in PEST_SERVICE_RATES:
                if pest in key and pest not in seen:
                    label = pest.title() if pest != 'rodent' else 'Rodent'
                    if pest == 'cockroach':
                        label = 'Cockroach'
                    elif pest == 'termite':
                        label = 'Termite'
                    found.append(label)
                    seen.add(pest)
                    break
    return found


def compute_service_rate_info(
    *,
    pest_type: str | None = None,
    pest_problems: str | None = None,
    service_frequency: str | None = None,
    estimated_price: Decimal | int | float | None = None,
) -> dict[str, Any]:
    """
    Build rate breakdown for PLAN + RATE UI.
    Uses fixed pest rates when pests are identified; falls back to estimated_price.
    """
    pests = parse_pest_names(pest_type, pest_problems)
    items: list[dict[str, Any]] = []
    total = 0
    for pest in pests:
        key = pest.lower()
        rate = PEST_SERVICE_RATES.get(key)
        if rate is not None:
            items.append({'pest': pest, 'rate': rate})
            total += rate

    plan = (service_frequency or 'one-time').strip()
    if plan.lower() in ('amc', 'annual', 'annual maintenance contract'):
        plan_label = 'AMC'
    else:
        plan_label = 'ONE TIME'

    if items:
        return {
            'plan': plan_label,
            'items': items,
            'total': total,
            'display_total': total,
            'rate_label': 'Service Rate',
            'has_service_rate': True,
        }

    if estimated_price is not None:
        try:
            amount = int(Decimal(str(estimated_price)))
        except Exception:
            amount = None
        if amount is not None and amount > 0:
            return {
                'plan': plan_label,
                'items': [],
                'total': amount,
                'display_total': amount,
                'rate_label': 'Quoted Price',
                'has_service_rate': False,
            }

    return {
        'plan': plan_label,
        'items': [],
        'total': None,
        'display_total': None,
        'rate_label': None,
        'has_service_rate': False,
    }
