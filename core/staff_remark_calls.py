"""Remark-Based Call Activities — staff performance from inquiry remarks.

Counts each NEW remark row once (CRM InquiryRemark + Website WebsiteLeadRemark)
by authenticated ``created_by`` and ``created_at``. Editing a remark (PATCH)
does not create a new row, so it does not inflate counts. Historical rows
count only in periods that include their ``created_at``.

These are labeled Remark-Based Call Activities (not verified phone call logs).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date


ACTIVITY_LABEL = 'Remark-Based Call Activities'
IST = 'Asia/Kolkata'


def _local_today() -> date:
    return timezone.localdate()


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    """Inclusive start / exclusive end in current Django timezone (IST)."""
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)
    return start, end


def _range_bounds(start_day: date | None, end_day: date | None) -> tuple[datetime | None, datetime | None]:
    start_dt = timezone.make_aware(datetime.combine(start_day, time.min)) if start_day else None
    end_dt = (
        timezone.make_aware(datetime.combine(end_day, time.min)) + timedelta(days=1)
        if end_day
        else None
    )
    return start_dt, end_dt


def _counts_by_user(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    staff_id: int | None = None,
) -> dict[int, dict[str, int]]:
    """Return {user_id: {crm, website, total}} for remark creates in range."""
    from core.models import InquiryRemark, WebsiteLeadRemark

    crm_filter = Q()
    web_filter = Q()
    if start is not None:
        crm_filter &= Q(created_at__gte=start)
        web_filter &= Q(created_at__gte=start)
    if end is not None:
        crm_filter &= Q(created_at__lt=end)
        web_filter &= Q(created_at__lt=end)
    if staff_id is not None:
        crm_filter &= Q(created_by_id=staff_id)
        web_filter &= Q(created_by_id=staff_id)

    crm_rows = (
        InquiryRemark.objects.filter(crm_filter, created_by_id__isnull=False)
        .values('created_by_id')
        .annotate(n=Count('id'))
    )
    web_rows = (
        WebsiteLeadRemark.objects.filter(web_filter, created_by_id__isnull=False)
        .values('created_by_id')
        .annotate(n=Count('id'))
    )

    out: dict[int, dict[str, int]] = {}
    for row in crm_rows:
        uid = row['created_by_id']
        bucket = out.setdefault(uid, {'crm': 0, 'website': 0, 'total': 0})
        bucket['crm'] = row['n']
        bucket['total'] += row['n']
    for row in web_rows:
        uid = row['created_by_id']
        bucket = out.setdefault(uid, {'crm': 0, 'website': 0, 'total': 0})
        bucket['website'] = row['n']
        bucket['total'] += row['n']
    return out


def _staff_queryset(staff_id: int | None = None):
    qs = User.objects.filter(is_active=True, is_staff=True).order_by('first_name', 'username')
    if staff_id is not None:
        qs = qs.filter(pk=staff_id)
    return qs


def count_for_period(period: str, staff_id: int | None = None) -> dict[int, dict[str, int]]:
    """Bucket counts for a named period (today, yesterday, last_7_days, this_month, total)."""
    today = _local_today()
    if period == 'yesterday':
        start, end = _day_bounds(today - timedelta(days=1))
        return _counts_by_user(start=start, end=end, staff_id=staff_id)
    if period == 'last_7_days':
        start, _ = _day_bounds(today - timedelta(days=6))
        _, end = _day_bounds(today)
        return _counts_by_user(start=start, end=end, staff_id=staff_id)
    if period == 'this_month':
        start, _ = _day_bounds(today.replace(day=1))
        _, end = _day_bounds(today)
        return _counts_by_user(start=start, end=end, staff_id=staff_id)
    if period == 'total':
        return _counts_by_user(staff_id=staff_id)
    # today (default)
    start, end = _day_bounds(today)
    return _counts_by_user(start=start, end=end, staff_id=staff_id)


def get_remark_call_activity_report(
    *,
    staff_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    """Full Staff Performance payload for Remark-Based Call Activities."""
    today = _local_today()
    staff_users = list(_staff_queryset(staff_id))

    today_map = count_for_period('today', staff_id=staff_id)
    yesterday_map = count_for_period('yesterday', staff_id=staff_id)
    last7_map = count_for_period('last_7_days', staff_id=staff_id)
    month_map = count_for_period('this_month', staff_id=staff_id)
    total_map = count_for_period('total', staff_id=staff_id)

    custom_map: dict[int, dict[str, int]] | None = None
    if from_date or to_date:
        start_dt, end_dt = _range_bounds(from_date, to_date or today)
        custom_map = _counts_by_user(start=start_dt, end=end_dt, staff_id=staff_id)

    def _row(user: User) -> dict[str, Any]:
        uid = user.id
        row: dict[str, Any] = {
            'staff_id': uid,
            'staff_name': user.get_full_name() or user.username,
            'today': today_map.get(uid, {}).get('total', 0),
            'today_crm': today_map.get(uid, {}).get('crm', 0),
            'today_website': today_map.get(uid, {}).get('website', 0),
            'yesterday': yesterday_map.get(uid, {}).get('total', 0),
            'last_7_days': last7_map.get(uid, {}).get('total', 0),
            'this_month': month_map.get(uid, {}).get('total', 0),
            'total': total_map.get(uid, {}).get('total', 0),
            'total_crm': total_map.get(uid, {}).get('crm', 0),
            'total_website': total_map.get(uid, {}).get('website', 0),
        }
        if custom_map is not None:
            row['custom'] = custom_map.get(uid, {}).get('total', 0)
            row['custom_crm'] = custom_map.get(uid, {}).get('crm', 0)
            row['custom_website'] = custom_map.get(uid, {}).get('website', 0)
        return row

    staff_rows = [_row(u) for u in staff_users]

    def _board(
        rows: list[dict[str, Any]],
        *,
        count_key: str,
        crm_key: str,
        website_key: str,
    ) -> list[dict[str, Any]]:
        return sorted(
            [
                {
                    'staff_id': r['staff_id'],
                    'staff_name': r['staff_name'],
                    'count': int(r.get(count_key) or 0),
                    'crm_count': int(r.get(crm_key) or 0),
                    'website_count': int(r.get(website_key) or 0),
                }
                for r in rows
            ],
            key=lambda x: (-x['count'], x['staff_name'].lower()),
        )

    # Today leaderboard: highest first, still include zeros for visibility
    today_board = _board(
        staff_rows, count_key='today', crm_key='today_crm', website_key='today_website'
    )

    # Active board for the UI date filter (custom range when from/to set).
    if custom_map is not None:
        selected_board = _board(
            staff_rows, count_key='custom', crm_key='custom_crm', website_key='custom_website'
        )
        range_from = from_date or to_date
        range_to = to_date or from_date or today
        selected_label = (
            range_from.isoformat()
            if range_from == range_to
            else f'{range_from.isoformat()} to {range_to.isoformat()}'
        )
    else:
        selected_board = today_board
        selected_label = 'today'

    return {
        'label': ACTIVITY_LABEL,
        'timezone': IST,
        'as_of': timezone.localtime().isoformat(),
        'filters': {
            'staff_id': staff_id,
            'from': from_date.isoformat() if from_date else None,
            'to': to_date.isoformat() if to_date else None,
        },
        'today': today_board,
        'selected': selected_board,
        'selected_label': selected_label,
        'staff': staff_rows,
    }


def parse_optional_date(value: str | None) -> date | None:
    if not value or not str(value).strip():
        return None
    return parse_date(str(value).strip())


def parse_optional_staff_id(value: str | None) -> int | None:
    if value is None or not str(value).strip():
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None
