"""
Helpers for combining JobCard schedule date + time_slot into a single sortable datetime.
"""
from __future__ import annotations

import re
from datetime import datetime

import pytz
from django.db import connection
from django.db.models import DateTimeField, F
from django.db.models.expressions import RawSQL
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
                        CASE
                            WHEN UPPER({table_name}.time_slot) LIKE '%%PM%%'
                                AND (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int BETWEEN 1 AND 11
                                THEN (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int + 12
                            WHEN UPPER({table_name}.time_slot) LIKE '%%AM%%'
                                AND (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int = 12
                                THEN 0
                            ELSE (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[1]::int
                        END,
                        (regexp_match({table_name}.time_slot, '(\\d{{1,2}}):(\\d{{2}})'))[2]::int,
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


def order_queryset_by_schedule_datetime(queryset, *, ascending: bool = True):
    """Apply stable ascending/descending schedule sort using the annotated field."""
    queryset = annotate_sort_schedule_datetime(queryset)
    sort_field = F('sort_schedule_datetime')
    if ascending:
        return queryset.order_by(sort_field.asc(nulls_last=True), 'id')
    return queryset.order_by(sort_field.desc(nulls_last=True), '-id')
