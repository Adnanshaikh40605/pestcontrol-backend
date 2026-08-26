"""Complaint call helpers: create one free linked service, never a new package."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from core.models import JobCard

logger = logging.getLogger(__name__)


def is_complaint_job(job: JobCard) -> bool:
    if getattr(job, 'is_complaint_call', False):
        return True
    if getattr(job, 'booking_category', None) == JobCard.BookingCategory.COMPLAINT_CALL:
        return True
    return getattr(job, 'booking_type', None) == JobCard.BookingType.COMPLAINT_CALL


def resolve_package_root(job: JobCard) -> JobCard:
    """Walk parent_job to the original package / booking root."""
    root = job
    seen: set[int] = set()
    while root.parent_job_id and root.parent_job_id not in seen:
        seen.add(root.id)
        parent = root.parent_job
        if parent is None:
            break
        root = parent
    return root


def _service_key(text: str | None) -> str:
    raw = (text or '').strip().lower()
    if not raw:
        return ''
    # Primary label only (multi-service packages use commas).
    primary = raw.split(',')[0].strip()
    return primary.replace(' ', '')[:24]


def _service_tokens(text: str | None) -> set[str]:
    """Tokenize multi-service labels for soft matching (Bed Bugs inside a package)."""
    raw = (text or '').strip().lower()
    if not raw:
        return set()
    parts = [p.strip() for p in raw.replace('/', ',').split(',') if p.strip()]
    tokens = set()
    for part in parts:
        compact = part.replace(' ', '')
        if compact:
            tokens.add(compact)
        # Also keep first word for loose match (cockroach, bed, rodent, termite).
        first = part.split()[0] if part.split() else ''
        if first and len(first) >= 3:
            tokens.add(first)
    return tokens


def _services_compatible(complaint_service: str | None, parent_service: str | None) -> bool:
    c_key = _service_key(complaint_service)
    p_key = _service_key(parent_service)
    if c_key and p_key and (c_key == p_key or c_key in p_key or p_key in c_key):
        return True
    c_tokens = _service_tokens(complaint_service)
    p_tokens = _service_tokens(parent_service)
    if not c_tokens or not p_tokens:
        return True  # no service info — allow candidate
    return bool(c_tokens & p_tokens)


def find_likely_complaint_parent(complaint: JobCard) -> Optional[JobCard]:
    """
    Best-effort link for historical complaints created without complaint_parent_booking.
    Prefers a prior Done root booking for the same client + service.
    """
    if complaint.complaint_parent_booking_id:
        return resolve_package_root(complaint.complaint_parent_booking)

    qs = (
        JobCard.objects.filter(
            client_id=complaint.client_id,
            status=JobCard.JobStatus.DONE,
            is_complaint_call=False,
        )
        .exclude(booking_category=JobCard.BookingCategory.COMPLAINT_CALL)
        .exclude(id=complaint.id)
        .select_related('parent_job')
        .order_by('-schedule_datetime', '-id')
    )

    candidates: list[JobCard] = []
    for job in qs[:120]:
        root = resolve_package_root(job)
        if root.is_complaint_call:
            continue
        if not _services_compatible(complaint.service_type, root.service_type):
            # Also try matching against the specific line job (e.g. Bed Bugs child).
            if not _services_compatible(complaint.service_type, job.service_type):
                continue
            # Prefer package root even when match was on a service line.
        if (
            complaint.schedule_datetime
            and root.schedule_datetime
            and root.schedule_datetime > complaint.schedule_datetime
        ):
            continue
        candidates.append(root)

    # Unique roots, closest prior first (already ordered).
    seen_roots: set[int] = set()
    ordered: list[JobCard] = []
    for root in candidates:
        if root.id in seen_roots:
            continue
        seen_roots.add(root.id)
        ordered.append(root)
    return ordered[0] if ordered else None


def apply_complaint_constraints(job: JobCard, parent: JobCard | None = None) -> list[str]:
    """
    Force a complaint JobCard to be a single free revisit service.
    Does not create follow-up visits or billable package economics.
    """
    changed: list[str] = []

    def setf(name: str, value) -> None:
        if getattr(job, name) != value:
            setattr(job, name, value)
            changed.append(name)

    setf('is_complaint_call', True)
    setf('booking_type', JobCard.BookingType.COMPLAINT_CALL)
    setf('booking_category', JobCard.BookingCategory.COMPLAINT_CALL)
    setf('price', '0')
    setf('total_amount', Decimal('0.00'))
    setf('service_cycle', 1)
    setf('max_cycle', 1)
    if hasattr(job, 'planned_visit_count'):
        setf('planned_visit_count', 1)
    setf('next_service_date', None)
    setf('is_followup_visit', False)
    setf('is_service_call', False)
    setf('included_in_amc', False)
    setf('is_amc_main_booking', False)
    setf('is_auto_generated', False)
    setf('service_category', JobCard.ServiceCategory.ONE_TIME)
    setf('payment_status', JobCard.PaymentStatus.PAID)

    if parent is not None:
        root = resolve_package_root(parent)
        if job.complaint_parent_booking_id != root.id:
            job.complaint_parent_booking = root
            changed.append('complaint_parent_booking')

    if not job.complaint_status:
        setf('complaint_status', JobCard.ComplaintStatus.OPEN)

    return changed


def create_complaint_jobcard(
    *,
    parent: JobCard,
    complaint_type: str,
    complaint_note: str = '',
    priority: str = 'Medium',
    revisit_date=None,
    technician_id=None,
    created_by=None,
    creation_source: str = JobCard.CreationSource.API,
) -> JobCard:
    """Create exactly one free complaint service linked to the original booking."""
    root = resolve_package_root(parent)

    schedule = None
    if revisit_date:
        if hasattr(revisit_date, 'hour'):
            schedule = revisit_date
        else:
            raw = str(revisit_date).strip()
            parsed_dt = parse_datetime(raw.replace('Z', '+00:00')) if raw else None
            if parsed_dt is not None:
                schedule = (
                    timezone.make_aware(parsed_dt, timezone.get_current_timezone())
                    if timezone.is_naive(parsed_dt)
                    else parsed_dt
                )
            else:
                day = parse_date(raw[:10]) if raw else None
                if day:
                    from datetime import datetime, time

                    # Default morning slot; CRM only sends a date today.
                    schedule = timezone.make_aware(
                        datetime.combine(day, time(hour=10)),
                        timezone.get_current_timezone(),
                    )

    complaint = JobCard(
        client=root.client,
        service_type=root.service_type,
        client_address=root.client_address,
        city=root.city,
        state=root.state,
        job_type=root.job_type,
        commercial_type=root.commercial_type,
        property_type=root.property_type,
        bhk_size=root.bhk_size,
        master_country=root.master_country,
        master_state=root.master_state,
        master_city=root.master_city,
        master_location=root.master_location,
        full_address=root.full_address,
        schedule_datetime=schedule,
        technician_id=technician_id or None,
        status=JobCard.JobStatus.PENDING,
        complaint_type=complaint_type or '',
        complaint_note=complaint_note or '',
        priority=priority or 'Medium',
        complaint_status=JobCard.ComplaintStatus.OPEN,
        created_by=created_by,
        creation_source=creation_source,
        # Explicitly NOT a package child — linked only via complaint_parent_booking.
        parent_job=None,
    )
    apply_complaint_constraints(complaint, parent=root)
    complaint.save()
    return complaint


def history_root_id(job: JobCard) -> int:
    """Original booking id this history row belongs under."""
    if is_complaint_job(job):
        if job.complaint_parent_booking_id:
            return resolve_package_root(job.complaint_parent_booking).id
        return job.id
    if job.parent_job_id:
        return resolve_package_root(job).id
    return job.id


def is_billable_root_booking(job: JobCard) -> bool:
    """True for original paid bookings — excludes complaints and package visits."""
    if is_complaint_job(job):
        return False
    if job.parent_job_id:
        return False
    if job.is_followup_visit or job.included_in_amc:
        return False
    if job.booking_category in (
        JobCard.BookingCategory.SERVICE_CALL,
        JobCard.BookingCategory.AMC_FOLLOWUP,
        JobCard.BookingCategory.COMPLAINT_CALL,
    ):
        return False
    if job.status == JobCard.JobStatus.CANCELLED:
        return False
    return True


def history_role(job: JobCard) -> str:
    if is_complaint_job(job):
        return 'complaint'
    if job.parent_job_id or job.is_followup_visit or job.included_in_amc:
        return 'service'
    if job.booking_category in (
        JobCard.BookingCategory.SERVICE_CALL,
        JobCard.BookingCategory.AMC_FOLLOWUP,
    ):
        return 'service'
    return 'booking'


def cancel_spurious_complaint_followups(complaint: JobCard, *, dry_run: bool = False) -> list[int]:
    """
    Cancel auto follow-up visits spawned from a complaint (Bed Bugs/AMC cycle 2+).
    Never cancels unrelated Done multi-service day-1 children unless they look like
    auto cycle follow-ups of the complaint itself.
    """
    cancelled: list[int] = []
    children = JobCard.objects.filter(parent_job=complaint).exclude(
        status=JobCard.JobStatus.CANCELLED,
    )
    for child in children:
        looks_like_followup = (
            child.is_followup_visit
            or (child.service_cycle or 1) > 1
            or child.creation_source == JobCard.CreationSource.AMC_AUTO
            or child.is_auto_generated
        )
        if not looks_like_followup:
            continue
        # Keep completed visits for audit trail — staff may have actually serviced them.
        if child.status == JobCard.JobStatus.DONE:
            continue
        cancelled.append(child.id)
        if dry_run:
            continue
        child.status = JobCard.JobStatus.CANCELLED
        child.cancellation_reason = (
            (child.cancellation_reason or '')
            + ' | Auto-cancelled: spurious follow-up created from complaint call'
        ).strip(' |')
        child.next_service_date = None
        child.max_cycle = child.service_cycle or 1
        child.save(update_fields=[
            'status', 'cancellation_reason', 'next_service_date', 'max_cycle', 'updated_at',
        ])
    return cancelled


@transaction.atomic
def heal_complaint_jobs(*, dry_run: bool = False, limit: int | None = None) -> dict:
    """
    Repair historical complaint rows:
    - link to original booking when missing
    - force free single-service constraints
    - cancel upcoming follow-ups incorrectly spawned from complaints
    """
    qs = (
        JobCard.objects.filter(
            Q(is_complaint_call=True)
            | Q(booking_category=JobCard.BookingCategory.COMPLAINT_CALL)
            | Q(booking_type=JobCard.BookingType.COMPLAINT_CALL)
        )
        .select_related('complaint_parent_booking', 'parent_job', 'client')
        .order_by('id')
    )
    if limit:
        qs = qs[:limit]

    linked = 0
    normalized = 0
    cancelled_ids: list[int] = []
    details: list[dict] = []

    for complaint in qs:
        parent = complaint.complaint_parent_booking
        if parent is None:
            parent = find_likely_complaint_parent(complaint)

        changed = apply_complaint_constraints(complaint, parent=parent)
        if parent and complaint.complaint_parent_booking_id == resolve_package_root(parent).id:
            if 'complaint_parent_booking' in changed:
                linked += 1

        if changed:
            normalized += 1
            if not dry_run:
                complaint.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))

        cancelled = cancel_spurious_complaint_followups(complaint, dry_run=dry_run)
        cancelled_ids.extend(cancelled)
        if changed or cancelled:
            details.append({
                'complaint_id': complaint.id,
                'parent_id': complaint.complaint_parent_booking_id,
                'changed_fields': changed,
                'cancelled_followups': cancelled,
            })

    return {
        'complaint_rows': qs.count() if limit is None else len(list(qs)),
        'normalized': normalized,
        'linked_parents': linked,
        'cancelled_followups': len(cancelled_ids),
        'cancelled_ids': cancelled_ids,
        'details': details,
        'dry_run': dry_run,
    }
