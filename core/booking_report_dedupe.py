"""Deduplicate BookingReportClient rows by mobile number."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count

from .models import BookingReportClient, BookingReportClientRemark


def normalize_mobile(value: str | None) -> str:
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if len(digits) > 10 and digits.startswith('91'):
        digits = digits[-10:]
    return digits[:20]


def _name_quality(name: str) -> tuple:
    """Higher tuple = better display name when merging duplicates."""
    raw = (name or '').strip()
    lower = raw.lower()
    digits = ''.join(ch for ch in raw if ch.isdigit())
    phone_like = bool(digits) and len(digits) >= 8 and len(digits) >= len(raw) - 3
    junk = (
        not raw
        or lower in {'unknown', '.', '-', 'na', 'n/a', 'none'}
        or phone_like
        or raw.startswith('+')
        or raw.replace(' ', '').isdigit()
    )
    return (0 if junk else 1, len(raw))


def choose_keeper(rows: list[BookingReportClient]) -> BookingReportClient:
    """
    Keep one row per mobile:
    1) most remarks
    2) best name quality
    3) lowest id (stable)
    """
    return min(
        rows,
        key=lambda r: (
            -int(getattr(r, '_remarks_len', 0) or 0),
            tuple(-x for x in _name_quality(r.name)),
            r.id,
        ),
    )


@transaction.atomic
def dedupe_booking_report_clients(*, dry_run: bool = False) -> dict:
    """
    Merge duplicate mobiles into a single BookingReportClient.
    Remarks on discarded rows are moved to the kept row.
    """
    dup_mobiles = list(
        BookingReportClient.objects.values('mobile')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
        .values_list('mobile', flat=True)
    )

    merged_groups = 0
    deleted_rows = 0
    moved_remarks = 0

    for mobile in dup_mobiles:
        rows = list(
            BookingReportClient.objects.filter(mobile=mobile)
            .annotate(_remarks_len=Count('remarks'))
            .order_by('id')
        )
        if len(rows) < 2:
            continue

        keeper = choose_keeper(rows)
        losers = [r for r in rows if r.id != keeper.id]

        best_name_row = max(rows, key=lambda r: _name_quality(r.name))
        if _name_quality(best_name_row.name) > _name_quality(keeper.name) and not dry_run:
            BookingReportClient.objects.filter(pk=keeper.pk).update(name=best_name_row.name[:255])

        loser_ids = [r.id for r in losers]
        if not dry_run:
            moved = BookingReportClientRemark.objects.filter(client_id__in=loser_ids).update(
                client_id=keeper.id
            )
            moved_remarks += moved
            BookingReportClient.objects.filter(id__in=loser_ids).delete()
            deleted_rows += len(loser_ids)
        else:
            moved_remarks += BookingReportClientRemark.objects.filter(client_id__in=loser_ids).count()
            deleted_rows += len(loser_ids)

        merged_groups += 1

    remaining = (
        BookingReportClient.objects.values('mobile')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
        .count()
    )

    return {
        'duplicate_groups': merged_groups,
        'deleted_rows': deleted_rows,
        'moved_remarks': moved_remarks,
        'remaining_duplicate_groups': remaining,
        'dry_run': dry_run,
    }
