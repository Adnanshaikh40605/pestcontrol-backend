"""Canonical booking reference / lead-source labels (keep in sync with CRM references.ts)."""

BOOKING_REFERENCE_OPTIONS: tuple[str, ...] = (
    'Website',
    'Google',
    'Play Store',
    'Previous Client',
    'Facebook',
    'YouTube',
    'LinkedIn',
    'SMS',
    'Calling Data',
    'Instagram',
    'WhatsApp',
    'Justdial',
    'Poster',
    'Friend Reference',
    'No Parking Board',
    'Holding',
    'Other',
)


def reference_counts_by_canonical_name(counts_by_raw_name: dict[str, int]) -> dict[str, int]:
    """Map stored reference strings onto canonical labels (case-insensitive)."""
    canonical_lower = {label.lower(): label for label in BOOKING_REFERENCE_OPTIONS}
    merged: dict[str, int] = {label: 0 for label in BOOKING_REFERENCE_OPTIONS}

    for raw_name, count in counts_by_raw_name.items():
        key = (raw_name or 'Other').strip().lower() or 'other'
        canonical = canonical_lower.get(key, raw_name or 'Other')
        merged[canonical] = merged.get(canonical, 0) + int(count or 0)

    return merged


def build_reference_report_rows(counts_by_raw_name: dict[str, int]) -> list[dict[str, int | str]]:
    """Rows for reference-report API: every canonical source + unknown extras."""
    merged = reference_counts_by_canonical_name(counts_by_raw_name)
    rows = [
        {'reference_name': label, 'reference_count': merged.get(label, 0)}
        for label in BOOKING_REFERENCE_OPTIONS
    ]

    known_lower = {label.lower() for label in BOOKING_REFERENCE_OPTIONS}
    for raw_name, count in counts_by_raw_name.items():
        key = (raw_name or '').strip().lower()
        if key and key not in known_lower:
            rows.append({
                'reference_name': raw_name,
                'reference_count': int(count or 0),
            })

    return rows
