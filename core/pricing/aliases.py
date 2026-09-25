"""Map legacy booking service labels onto 2026 Pricing Master packages.

Older website/CRM bookings store names such as "Cockroach / Ants". The 2026
rate chart renamed those into tiers ("Cockroach Standard", "Cockroach Premium").
Lookups must resolve the legacy label to a live package without inventing
prices — only packages that already have PricingRate rows are returned.
"""

from __future__ import annotations

import re

# Preferred target first. Callers pick the first candidate that exists in the
# live rate matrix / DB for the region.
LEGACY_SERVICE_PACKAGE_ALIASES: dict[str, tuple[str, ...]] = {
    'Cockroach / Ants': ('Cockroach Standard', 'Cockroach Premium'),
    'Cockroach': ('Cockroach Standard', 'Cockroach Premium'),
    'Ants': ('Cockroach Standard', 'Cockroach Premium'),
    # Website used to send these marketing labels as JobCard.service_type.
    'Cockroach Control': ('Cockroach Standard', 'Cockroach Premium'),
    'Ant Control': ('Cockroach Standard', 'Cockroach Premium'),
    'Cockroach Control, Ant Control': ('Cockroach Standard', 'Cockroach Premium'),
    'Rodent': ('Regular Rodent', 'Kill-Rodent System'),
    'Mosquito': ('Mosquito Cold Fogging', 'Mosquito Thermal Fogging'),
    'Termite': ('Termite Spot Treatment', 'Termite'),
    'General Pest': ('General Pest Control',),
}

# Services that still accept the legacy "Commercial" catch-all area (amount 0 =
# inspection / quote after visit) on office/hotel/society/other bookings.
COMMERCIAL_CATCHALL_SERVICES: frozenset[str] = frozenset({
    'Cockroach / Ants',
    'Cockroach Standard',
    'Cockroach Premium',
    'Rodent',
    'Regular Rodent',
    'Kill-Rodent System',
    'Mosquito',
    'Mosquito Cold Fogging',
    'Mosquito Thermal Fogging',
    'Bed Bugs',
    'Termite',
    'Termite Spot Treatment',
    'General Pest Control',
})

COCKROACH_FAMILY = frozenset({
    'Cockroach / Ants',
    'Cockroach Standard',
    'Cockroach Premium',
    'Cockroach Control',
    'Ant Control',
    'Cockroach Control, Ant Control',
    'Ant Control, Cockroach Control',
    'Cockroach',
    'Ants',
})

# Live chart packages — never treat these as "legacy dual" labels to merge away.
COCKROACH_LIVE_PACKAGES = frozenset({
    'Cockroach Standard',
    'Cockroach Premium',
})


def _norm(name: str) -> str:
    return ' '.join((name or '').strip().split())


def alias_candidates(service: str) -> tuple[str, ...]:
    """Return lookup candidates for a stored service label (self first)."""
    name = _norm(service)
    if not name:
        return ()
    # Comma-joined legacy website label → treat as one cockroach family package.
    if ',' in name:
        parts = [p.strip() for p in name.split(',') if p.strip()]
        legacy_pair = {'Cockroach Control', 'Ant Control'}
        if parts and set(parts) <= legacy_pair:
            return alias_candidates('Cockroach Control')
    aliases = LEGACY_SERVICE_PACKAGE_ALIASES.get(name, ())
    ordered: list[str] = []
    for candidate in (name, *aliases):
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return tuple(ordered)


def _prefer_cockroach_live_package(names: list[str]) -> str:
    """Pick Cockroach Premium when any label says premium; else Standard."""
    if any('premium' in (n or '').casefold() for n in names):
        return 'Cockroach Premium'
    for name in names:
        resolved = resolve_service_package(name)
        if resolved in COCKROACH_LIVE_PACKAGES:
            return resolved
    return 'Cockroach Standard'


def coalesce_cockroach_family_service_names(names: list[str]) -> list[str]:
    """Collapse Ant Control + Cockroach Control (+ legacy) into one live package name.

    Real multi-service packages (e.g. Cockroach + Bed Bugs) keep both lines.
    """
    cockroach: list[str] = []
    others: list[str] = []
    for raw in names:
        name = _norm(raw)
        if not name:
            continue
        if is_cockroach_family(name):
            cockroach.append(name)
        else:
            others.append(name)
    if not cockroach:
        return list(names)
    live = _prefer_cockroach_live_package(cockroach)
    return [live, *others]


def coalesce_cockroach_family_service_items(items: list | None) -> list[dict]:
    """Merge cockroach-family service_items rows into one Cockroach Standard/Premium line.

    Website "Cockroach / Ants" used to land as Ant Control + Cockroach Control
    (two rows). Visit generation then created a MULTI SERVICE PACKAGE shell plus
    two day-1 children. One combined row prevents that.
    """
    if not items:
        return []

    from core.payment_utils import parse_jobcard_price

    cockroach: list[dict] = []
    others: list[dict] = []
    for raw in items:
        item = dict(raw or {})
        name = _norm(str(item.get('service') or ''))
        if name and is_cockroach_family(name):
            cockroach.append(item)
        else:
            others.append(item)

    if not cockroach:
        return [dict(raw or {}) for raw in items]

    live = _prefer_cockroach_live_package(
        [_norm(str(i.get('service') or '')) for i in cockroach],
    )

    if len(cockroach) == 1:
        merged = dict(cockroach[0])
        merged['service'] = live
        return [merged, *others]

    amount = sum(float(parse_jobcard_price(i.get('amount'))) for i in cockroach)
    discount = sum(float(parse_jobcard_price(i.get('discount'))) for i in cockroach)
    base = sum(
        float(parse_jobcard_price(i.get('base_amount', i.get('amount'))))
        for i in cockroach
    )
    plan = next(
        (str(i.get('plan') or i.get('frequency') or '').strip() for i in cockroach if str(i.get('plan') or i.get('frequency') or '').strip()),
        '',
    )
    area = next(
        (str(i.get('area') or '').strip() for i in cockroach if str(i.get('area') or '').strip()),
        '',
    )
    merged = {
        'service': live,
        'plan': plan,
        'area': area,
        'amount': amount,
        'discount': discount,
        'base_amount': base if base > 0 else amount,
    }
    return [merged, *others]


def resolve_service_package(
    service: str,
    available: set[str] | frozenset[str] | None = None,
) -> str:
    """Pick the best live Pricing Master package for a stored service label.

    When ``available`` is given, only packages in that set are chosen. Known
    legacy labels prefer their 2026 chart targets even if the old name is still
    present (e.g. after a partial import). Without ``available``, returns the
    preferred chart name for known legacy labels, otherwise the normalised input.
    """
    name = _norm(service)
    if not name:
        return ''

    if available is not None:
        aliases = LEGACY_SERVICE_PACKAGE_ALIASES.get(name)
        if aliases:
            for candidate in aliases:
                if candidate in available:
                    return candidate
            if name in available:
                return name
        for candidate in alias_candidates(name):
            if candidate in available:
                return candidate
        lower = name.casefold()
        fuzzy: list[str] = []
        if 'cockroach' in lower or lower in {'ants', 'ant'} or re.search(r'\bants?\b', lower):
            fuzzy = ['Cockroach Standard', 'Cockroach Premium']
        elif 'rodent' in lower or lower in {'rat', 'rats'}:
            fuzzy = ['Regular Rodent', 'Kill-Rodent System']
        elif 'mosquito' in lower:
            fuzzy = ['Mosquito Cold Fogging', 'Mosquito Thermal Fogging']
        elif 'termite' in lower:
            fuzzy = ['Termite Spot Treatment', 'Termite']
        for candidate in fuzzy:
            if candidate in available:
                return candidate
        return name

    aliases = LEGACY_SERVICE_PACKAGE_ALIASES.get(name)
    if aliases:
        return aliases[0]
    return name


def packages_for_area_lookup(service: str) -> tuple[str, ...]:
    """All package names to query when collecting area options for one service."""
    return alias_candidates(service)


def is_cockroach_family(service: str) -> bool:
    name = _norm(service)
    if name in COCKROACH_FAMILY:
        return True
    lower = name.casefold()
    return 'cockroach' in lower or lower in {'ants', 'ant'}


def clean_service_label(service: str) -> str:
    """Drop emoji and extra spacing from a stored service label."""
    raw = re.sub(r'[^\w\s/&+\-]', ' ', service or '', flags=re.UNICODE)
    return _norm(raw)


def canonical_service_line(service: str) -> str:
    """One key for legacy and 2026 names of the same package line.

    ``Cockroach / Ants`` and ``Cockroach Standard`` compare equal.
    ``Cockroach Premium`` stays distinct from Standard.
    """
    name = clean_service_label(service)
    if not name:
        return ''
    return resolve_service_package(name) or name


def same_service_line(left: str, right: str) -> bool:
    a = canonical_service_line(left)
    b = canonical_service_line(right)
    return bool(a) and a.casefold() == b.casefold()


def is_package_blob_label(service: str) -> bool:
    """Combined marketing label, not one service line (e.g. Cockroach + Bed Bugs)."""
    name = clean_service_label(service)
    if not name:
        return False
    folded = name.casefold()
    if 'multiple pest' in folded:
        return True
    parts = [p.strip() for p in name.split(',') if p.strip()]
    if len(parts) < 2:
        return False
    # "Cockroach Control, Ant Control" is one cockroach package, not a multi blob.
    legacy_pair = {'cockroach control', 'ant control'}
    if {p.casefold() for p in parts} <= legacy_pair:
        return False
    return True
