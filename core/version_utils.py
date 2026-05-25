"""Semantic version comparison for partner app force-update."""

from __future__ import annotations


def normalize_version(version: str) -> str:
    """Strip build metadata (e.g. 2.0.0+1 -> 2.0.0)."""
    if not version:
        return '0.0.0'
    v = str(version).strip()
    if '+' in v:
        v = v.split('+', 1)[0]
    if '-' in v and not v[0].isdigit():
        pass
    return v or '0.0.0'


def parse_version_parts(version: str) -> tuple[int, ...]:
    normalized = normalize_version(version)
    parts: list[int] = []
    for segment in normalized.split('.'):
        segment = segment.strip()
        if not segment:
            parts.append(0)
            continue
        num = ''
        for ch in segment:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def compare_versions(left: str, right: str) -> int:
    """
    Compare two version strings.
    Returns -1 if left < right, 0 if equal, 1 if left > right.
    """
    a = parse_version_parts(left)
    b = parse_version_parts(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def is_version_below(current: str, minimum: str) -> bool:
    return compare_versions(current, minimum) < 0
