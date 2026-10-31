"""Today's technician assignment report for the CRM bookings page.

A row is included when the visit is scheduled today in Asia/Kolkata and the
lead technician is active. Cancelled visits and technicians marked inactive
stay off the page.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.utils import timezone

from core.models import JobCard

IST = ZoneInfo('Asia/Kolkata')

_SPECIAL_PRICE_LABELS = {
    'Free (Complaint)',
    'Included in AMC',
    'Included in Service',
}


def _ist_day_bounds(now=None):
    if now is None:
        now = timezone.now()
    if timezone.is_naive(now):
        now = timezone.make_aware(now, timezone.utc)
    day = now.astimezone(IST).date()
    start = datetime.combine(day, time.min, tzinfo=IST)
    return day, start, start + timedelta(days=1)


def _price_label(job) -> str:
    from core.serializers import JobCardSerializer

    raw = JobCardSerializer().get_price_display(job)
    text = '' if raw is None else str(raw).strip()
    if text in _SPECIAL_PRICE_LABELS:
        return text
    try:
        amount = Decimal(text or '0')
    except (InvalidOperation, ValueError):
        return text or '₹0'
    if amount == amount.to_integral():
        shown = f'{int(amount):,}'
    else:
        shown = f'{amount:,.2f}'
    return f'₹{shown}'


def _location(job) -> str:
    area = ''
    if job.master_location_id and job.master_location:
        area = (job.master_location.name or '').strip()
    city = ''
    if job.master_city_id and job.master_city:
        city = (job.master_city.name or '').strip()
    if not city:
        city = (job.city or '').strip()
    if area and city and area.lower() != city.lower():
        return f'{area}, {city}'
    if area or city:
        return area or city
    return (job.client_address or job.full_address or '').strip()


def _job_row(job) -> dict:
    client = job.client
    return {
        'id': job.id,
        'customer_name': (client.full_name if client else '') or '',
        'customer_mobile': (client.mobile if client else '') or '',
        'service_type': job.service_type or '',
        'price_label': _price_label(job),
        'location': _location(job),
        'status': job.status or '',
        'time_slot': (job.time_slot or '').strip(),
    }


def build_today_technician_report(now=None) -> dict:
    day, start, end = _ist_day_bounds(now)
    jobs = (
        JobCard.objects.filter(
            technician_id__isnull=False,
            technician__is_active=True,
            schedule_datetime__gte=start,
            schedule_datetime__lt=end,
        )
        .exclude(status=JobCard.JobStatus.CANCELLED)
        .exclude(
            parent_job_id__isnull=False,
            service_cycle=1,
            is_auto_generated=True,
            is_complaint_call=False,
        )
        .select_related('client', 'technician', 'master_location', 'master_city')
        .order_by('schedule_datetime', 'id')
    )

    grouped: dict[int, dict] = {}
    for job in jobs:
        tech = job.technician
        bucket = grouped.get(tech.id)
        if bucket is None:
            bucket = {
                'id': tech.id,
                'name': tech.name or '',
                'mobile': tech.mobile or '',
                'booking_count': 0,
                'locations': [],
                '_location_keys': set(),
                'jobs': [],
            }
            grouped[tech.id] = bucket
        row = _job_row(job)
        bucket['jobs'].append(row)
        bucket['booking_count'] += 1
        location = row['location']
        key = location.lower()
        if location and key not in bucket['_location_keys']:
            bucket['_location_keys'].add(key)
            bucket['locations'].append(location)

    technicians = []
    for bucket in grouped.values():
        bucket.pop('_location_keys', None)
        technicians.append(bucket)
    technicians.sort(key=lambda row: (-row['booking_count'], row['name'].casefold(), row['id']))

    return {
        'date': day.isoformat(),
        'technician_count': len(technicians),
        'booking_count': sum(row['booking_count'] for row in technicians),
        'technicians': technicians,
    }
