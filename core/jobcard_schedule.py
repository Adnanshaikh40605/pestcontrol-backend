"""
Helpers for combining JobCard schedule date + time_slot into a single sortable datetime.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

import pytz
from django.db import connection
from django.db.models import Case, DateTimeField, F, IntegerField, Value, When
from django.db.models.expressions import RawSQL
from django.db.models.functions import TruncDate
from django.utils import timezone

IST = pytz.timezone('Asia/Kolkata')
TIME_RE = re.compile(r'(\d{1,2}):(\d{2})')
AMPM_RE = re.compile(r'(AM|PM)', re.I)


def parse_time_slot(time_slot: str | None) -> tuple[int, int] | None:
    """Parse the first HH:MM (+ optional AM/PM) from a time_slot string."""
    if not time_slot or not str(time_slot).strip():
        return None
    match = TIME_RE.search(str(time_slot))
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    ampm_match = AMPM_RE.search(str(time_slot))
    ampm = ampm_match.group(1).upper() if ampm_match else None
    if ampm == 'PM' and hours < 12:
        hours += 12
    elif ampm == 'AM' and hours == 12:
        hours = 0
    return hours, minutes


def effective_schedule_datetime(schedule_datetime, time_slot: str | None):
    """
    Return a timezone-aware datetime for sorting/display.

    When time_slot is present, use the schedule date in IST with the parsed slot time.
    This matches CRM display logic (time_slot overrides schedule time).
    """
    if not schedule_datetime:
        return None
    if not timezone.is_aware(schedule_datetime):
        schedule_datetime = timezone.make_aware(schedule_datetime, timezone.utc)
    parsed = parse_time_slot(time_slot)
    if parsed:
        hours, minutes = parsed
        local = schedule_datetime.astimezone(IST)
        combined = IST.localize(
            datetime(local.year, local.month, local.day, hours, minutes, 0)
        )
        return combined.astimezone(timezone.utc)
    return schedule_datetime


def _postgres_sort_schedule_sql(table_name: str) -> str:
    return f"""
    CASE
        WHEN {table_name}.schedule_datetime IS NULL THEN NULL
        WHEN {table_name}.time_slot IS NOT NULL AND BTRIM({table_name}.time_slot) <> '' THEN (
            (
                DATE({table_name}.schedule_datetime AT TIME ZONE 'Asia/Kolkata')
                + CASE
                    WHEN (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})')) IS NULL
                        THEN TIME '00:00'
                    ELSE make_time(
                        LEAST(GREATEST(
                            CASE
                                WHEN UPPER({table_name}.time_slot) LIKE '%%PM%%'
                                    AND (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int BETWEEN 1 AND 11
                                    THEN (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int + 12
                                WHEN UPPER({table_name}.time_slot) LIKE '%%AM%%'
                                    AND (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int = 12
                                    THEN 0
                                ELSE (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int
                            END,
                        0), 23),
                        LEAST(GREATEST(
                            (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[2]::int,
                        0), 59),
                        0
                    )
                END
            ) AT TIME ZONE 'Asia/Kolkata'
        )
        ELSE {table_name}.schedule_datetime
    END
    """


def annotate_sort_schedule_datetime(queryset, *, table_name: str | None = None):
    """
    Annotate queryset with sort_schedule_datetime for DB-level ordering.

    PostgreSQL uses a SQL expression that merges time_slot into the schedule date (IST).
    Other databases fall back to schedule_datetime (tests use normalized saves).
    """
    if connection.vendor == 'postgresql':
        table = table_name or queryset.model._meta.db_table
        return queryset.annotate(
            sort_schedule_datetime=RawSQL(
                _postgres_sort_schedule_sql(table),
                [],
                output_field=DateTimeField(),
            )
        )
    return queryset.annotate(sort_schedule_datetime=F('schedule_datetime'))


def _ist_today_and_tomorrow() -> tuple:
    today = timezone.now().astimezone(IST).date()
    return today, today + timedelta(days=1)


def _annotate_date_priority(queryset, date_field: str):
    """Tier: 0=today, 1=tomorrow, 2=future, 3=past, 4=null."""
    today, tomorrow = _ist_today_and_tomorrow()
    return queryset.annotate(
        sort_priority=Case(
            When(**{f'{date_field}__isnull': True}, then=Value(4)),
            When(**{date_field: today}, then=Value(0)),
            When(**{date_field: tomorrow}, then=Value(1)),
            When(**{f'{date_field}__gt': tomorrow}, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    )


def order_queryset_by_reminder_date(queryset, *, ascending: bool = True):
    """Sort reminders: today, tomorrow, future, then overdue; time ascending within a day."""
    queryset = _annotate_date_priority(queryset, 'reminder_date')
    if ascending:
        return queryset.order_by(
            'sort_priority',
            F('reminder_date').asc(nulls_last=True),
            F('reminder_time').asc(nulls_last=True),
            'id',
        )
    return queryset.order_by(
        'sort_priority',
        F('reminder_date').desc(nulls_last=True),
        F('reminder_time').desc(nulls_last=True),
        '-id',
    )


def order_queryset_by_schedule_datetime(queryset, *, ascending: bool = True):
    """
    Sort bookings: today, tomorrow, future, then overdue past dates.
    Within each tier, order by combined schedule date + time_slot ascending.
    """
    queryset = annotate_sort_schedule_datetime(queryset)
    today, tomorrow = _ist_today_and_tomorrow()
    queryset = queryset.annotate(
        schedule_ist_date=TruncDate('sort_schedule_datetime', tzinfo=IST),
    )
    queryset = queryset.annotate(
        sort_priority=Case(
            When(sort_schedule_datetime__isnull=True, then=Value(4)),
            When(schedule_ist_date=today, then=Value(0)),
            When(schedule_ist_date=tomorrow, then=Value(1)),
            When(schedule_ist_date__gt=tomorrow, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    )
    sort_field = F('sort_schedule_datetime')
    if ascending:
        return queryset.order_by(
            'sort_priority',
            sort_field.asc(nulls_last=True),
            'id',
        )
    return queryset.order_by(
        'sort_priority',
        sort_field.desc(nulls_last=True),
        '-id',
    )
