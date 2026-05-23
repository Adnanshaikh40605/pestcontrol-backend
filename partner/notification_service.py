"""
Partner in-app notification records + CRM event log (no push / Firebase).
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from core.models import JobCard, Technician
from partner.models import CrmPartnerEvent, Partner, PartnerNotification

logger = logging.getLogger(__name__)


def _booking_subtitle(job: JobCard) -> str:
    job = JobCard.objects.select_related('client', 'master_location', 'master_city').filter(pk=job.pk).first() or job
    service = job.service_type or 'Service'
    area = ''
    if job.master_location:
        area = job.master_location.name
    elif job.city:
        area = job.city
    elif job.client and job.client.city:
        area = job.client.city
    if area:
        return f'{service} - {area}'
    return service


def _partner_ids_for_technician(technician_id: int | None) -> list[int] | None:
    """None = all approved partners; list = specific partner PKs only."""
    if not technician_id:
        return None
    try:
        tech = Technician.objects.select_related('partner_account').get(pk=technician_id)
    except Technician.DoesNotExist:
        logger.warning('send-to-app: technician %s not found, broadcasting to all', technician_id)
        return None
    partner = getattr(tech, 'partner_account', None)
    if not partner or not partner.is_active or not partner.is_app_approved:
        logger.warning('send-to-app: technician %s has no approved partner app', technician_id)
        return []
    return [partner.id]


def approved_partner_ids(technician_id: int | None = None) -> list[int]:
    """Partner PKs that receive pool broadcast / in-app new-booking alerts."""
    qs = Partner.objects.filter(is_active=True, is_app_approved=True)
    target = _partner_ids_for_technician(technician_id)
    if target is not None:
        if not target:
            return []
        qs = qs.filter(pk__in=target)
    return list(qs.values_list('pk', flat=True))


def _notify_dedupe_key(
    job_id: int,
    notification_type: str,
    *,
    technician_id: int | None = None,
    partner_id: int | None = None,
) -> str:
    if partner_id is not None:
        scope = f'p{partner_id}'
    elif technician_id is not None:
        scope = f'tech{technician_id}'
    else:
        scope = 'all'
    return f'partner_notify:{job_id}:{notification_type}:{scope}'


def should_skip_duplicate_notify(
    job_id: int,
    notification_type: str,
    technician_id: int | None = None,
    partner_id: int | None = None,
) -> bool:
    key = _notify_dedupe_key(job_id, notification_type, technician_id=technician_id, partner_id=partner_id)
    if cache.get(key):
        return True
    cache.set(key, True, timeout=90)
    return False


def create_partner_notification(
    partner: Partner,
    *,
    notification_type: str,
    title: str,
    body: str,
    booking: JobCard | None = None,
    data: dict[str, Any] | None = None,
) -> PartnerNotification:
    return PartnerNotification.objects.create(
        partner=partner,
        notification_type=notification_type,
        title=title,
        body=body,
        booking=booking,
        data=data or {},
    )


def log_crm_partner_event(job: JobCard, event_type: str, message: str, extra: dict | None = None) -> CrmPartnerEvent:
    return CrmPartnerEvent.objects.create(
        job=job,
        event_type=event_type,
        message=message,
        data=extra or {},
    )


def notify_partners_new_booking(
    job: JobCard,
    technician_id: int | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """
    Create in-app notifications for approved partners when CRM sends a booking to the app.
    """
    if not force and should_skip_duplicate_notify(
        job.id,
        PartnerNotification.NotificationType.NEW_BOOKING,
        technician_id,
    ):
        logger.info('Skipping duplicate in-app notify for job #%s', job.id)
        return {'skipped': True, 'partners_notified': 0, 'approved_partner_count': 0}

    title = 'New Booking Available'
    body = _booking_subtitle(job)
    data = {
        'type': PartnerNotification.NotificationType.NEW_BOOKING,
        'booking_id': str(job.id),
        'job_code': job.code or '',
    }

    partner_ids = approved_partner_ids(technician_id)
    partners_qs = Partner.objects.filter(pk__in=partner_ids)

    for partner in partners_qs:
        create_partner_notification(
            partner,
            notification_type=PartnerNotification.NotificationType.NEW_BOOKING,
            title=title,
            body=body,
            booking=job,
            data=data,
        )

    logger.info(
        'In-app notify job #%s: approved_partners=%s',
        job.id,
        len(partner_ids),
    )

    log_crm_partner_event(
        job,
        CrmPartnerEvent.EventType.BOOKING_SENT_TO_APP,
        f'In-app notification for {len(partner_ids)} partner(s)',
        {
            'technician_id': technician_id,
            'approved_partner_ids': partner_ids,
            'partners_notified': len(partner_ids),
        },
    )
    return {
        'skipped': False,
        'partners_notified': len(partner_ids),
        'approved_partner_count': len(partner_ids),
    }


notify_all_partners_new_booking = notify_partners_new_booking


def notify_partner_assigned(job: JobCard, partner: Partner) -> None:
    if should_skip_duplicate_notify(
        job.id,
        PartnerNotification.NotificationType.BOOKING_ASSIGNED,
        partner_id=partner.id,
    ):
        return
    title = 'Booking Assigned'
    body = _booking_subtitle(job)
    data = {
        'type': PartnerNotification.NotificationType.BOOKING_ASSIGNED,
        'booking_id': str(job.id),
        'job_code': job.code or '',
    }
    create_partner_notification(
        partner,
        notification_type=PartnerNotification.NotificationType.BOOKING_ASSIGNED,
        title=title,
        body=body,
        booking=job,
        data=data,
    )


def notify_crm_booking_accepted(job: JobCard, partner: Partner) -> None:
    msg = f'{partner.full_name} accepted Booking #{job.code or job.id}'
    log_crm_partner_event(job, CrmPartnerEvent.EventType.BOOKING_ACCEPTED, msg, {'partner_id': partner.id})


def notify_crm_service_started(job: JobCard, partner: Partner) -> None:
    msg = f'{partner.full_name} started service for Booking #{job.code or job.id}'
    log_crm_partner_event(job, CrmPartnerEvent.EventType.SERVICE_STARTED, msg, {'partner_id': partner.id})


def notify_crm_service_completed(job: JobCard, partner: Partner) -> None:
    msg = f'{partner.full_name} completed Booking #{job.code or job.id}'
    log_crm_partner_event(job, CrmPartnerEvent.EventType.JOB_COMPLETED, msg, {'partner_id': partner.id})


def notify_partner_booking_cancelled(job: JobCard, partner: Partner | None = None) -> None:
    if should_skip_duplicate_notify(job.id, PartnerNotification.NotificationType.BOOKING_CANCELLED):
        return
    title = 'Booking Cancelled'
    body = f'Booking #{job.code or job.id} was cancelled'
    data = {
        'type': PartnerNotification.NotificationType.BOOKING_CANCELLED,
        'booking_id': str(job.id),
    }
    partners_qs = Partner.objects.filter(is_active=True, is_app_approved=True)
    if partner:
        partners_qs = partners_qs.filter(pk=partner.pk)
    for p in partners_qs:
        create_partner_notification(
            p,
            notification_type=PartnerNotification.NotificationType.BOOKING_CANCELLED,
            title=title,
            body=body,
            booking=job,
            data=data,
        )
