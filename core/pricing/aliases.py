"""Map legacy booking service labels onto 2026 Pricing Master packages.

Older website/CRM bookings store names such as "Cockroach / Ants". The 2026
rate chart renamed those into tiers ("Cockroach Standard", "Cockroach Premium").
Lookups must resolve the legacy label to a live package without inventing
prices — only packages that already have PricingRate rows are returned.
"""

from __future__ import annotations

# Preferred target first. Callers pick the first candidate that exists in the
# live rate matrix / DB for the region.
LEGACY_SERVICE_PACKAGE_ALIASES: dict[str, tuple[str, ...]] = {
    'Cockroach / Ants': ('Cockroach Standard', 'Cockroach Premium'),
    'Cockroach': ('Cockroach Standard', 'Cockroach Premium'),
    'Ants': ('Cockroach Standard', 'Cockroach Premium'),
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
})


def _norm(name: str) -> str:
    return ' '.join((name or '').strip().split())


def alias_candidates(service: str) -> tuple[str, ...]:
    """Return lookup candidates for a stored service label (self first)."""
    name = _norm(service)
    if not name:
        return ()
    aliases = LEGACY_SERVICE_PACKAGE_ALIASES.get(name, ())
    ordered: list[str] = []
    for candidate in (name, *aliases):
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return tuple(ordered)


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
        if 'cockroach' in lower or lower in {'ants', 'ant'}:
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
