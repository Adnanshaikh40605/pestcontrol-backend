"""
Partner push + in-app notification records + CRM event log.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from core.models import JobCard, Technician
from partner.models import CrmPartnerEvent, Partner, PartnerDeviceToken, PartnerNotification
from partner.push_service import (
    is_fcm_configured,
    send_push_to_tokens,
    should_skip_duplicate_push,
)

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


def register_device_token(partner: Partner, fcm_token: str, device_type: str = 'android') -> PartnerDeviceToken:
    fcm_token = (fcm_token or '').strip()
    if not fcm_token:
        raise ValueError('FCM token is required')

    existing = PartnerDeviceToken.objects.filter(fcm_token=fcm_token).first()
    if existing:
        existing.partner = partner
        existing.device_type = device_type or existing.device_type
        existing.is_active = True
        existing.last_used_at = timezone.now()
        existing.save(update_fields=['partner', 'device_type', 'is_active', 'last_used_at'])
    else:
        existing = PartnerDeviceToken.objects.create(
            partner=partner,
            fcm_token=fcm_token,
            device_type=device_type or 'android',
            is_active=True,
        )

    Partner.objects.filter(pk=partner.pk).update(fcm_token=fcm_token)

    if partner.fcm_token and partner.fcm_token != fcm_token:
        old = partner.fcm_token.strip()
        if old:
            PartnerDeviceToken.objects.filter(fcm_token=old, partner=partner).update(is_active=False)

    logger.info('FCM token registered partner=%s device=%s', partner.id, device_type)
    return existing


def deactivate_device_token(partner: Partner, fcm_token: str | None = None) -> int:
    qs = PartnerDeviceToken.objects.filter(partner=partner, is_active=True)
    if fcm_token:
        qs = qs.filter(fcm_token=fcm_token.strip())
    count = qs.update(is_active=False)
    if not fcm_token:
        Partner.objects.filter(pk=partner.pk).update(fcm_token=None)
    elif partner.fcm_token == fcm_token:
        Partner.objects.filter(pk=partner.pk).update(fcm_token=None)
    return count


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


def active_tokens_for_partners(partner_ids: list[int] | None = None) -> list[str]:
    qs = PartnerDeviceToken.objects.filter(is_active=True).select_related('partner')
    if partner_ids is not None:
        if not partner_ids:
            return []
        qs = qs.filter(partner_id__in=partner_ids)
    else:
        qs = qs.filter(partner__is_active=True, partner__is_app_approved=True)
    return list(dict.fromkeys(qs.values_list('fcm_token', flat=True)))


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
) -> dict[str, int]:
    """
    Push new booking to partner app.
    - technician_id set → only that technician's partner (CRM "send to specific technician")
    - technician_id omitted → all approved active partners (pool broadcast)
    - force=True → CRM refloat; always send FCM again (skip 90s dedupe)
    """
    if not force and should_skip_duplicate_push(
        job.id,
        PartnerNotification.NotificationType.NEW_BOOKING,
        technician_id,
    ):
        logger.info('Skipping duplicate push for job #%s', job.id)
        return {
            'success': 0,
            'failure': 0,
            'skipped': True,
            'fcm_configured': is_fcm_configured(),
        }

    title = 'New Booking Available'
    body = _booking_subtitle(job)
    data = {
        'type': PartnerNotification.NotificationType.NEW_BOOKING,
        'booking_id': str(job.id),
        'job_code': job.code or '',
    }
    collapse_key = f'booking_{job.id}'

    target_partner_ids = _partner_ids_for_technician(technician_id)
    partners_qs = Partner.objects.filter(is_active=True, is_app_approved=True)
    if target_partner_ids is not None:
        partners_qs = partners_qs.filter(pk__in=target_partner_ids)

    for partner in partners_qs:
        create_partner_notification(
            partner,
            notification_type=PartnerNotification.NotificationType.NEW_BOOKING,
            title=title,
            body=body,
            booking=job,
            data=data,
        )

    tokens = active_tokens_for_partners(target_partner_ids)
    result = send_push_to_tokens(
        tokens,
        title=title,
        body=body,
        data=data,
        collapse_key=collapse_key,
        channel_id='pest99_new_booking_v2',
        sound='uber_driver_sound',
        data_only=True,
    )
    result['skipped'] = False
    result['fcm_configured'] = is_fcm_configured()

    log_crm_partner_event(
        job,
        CrmPartnerEvent.EventType.BOOKING_SENT_TO_APP,
        f'Push sent to {len(tokens)} device(s)',
        {
            'fcm_success': result.get('success', 0),
            'fcm_failure': result.get('failure', 0),
            'technician_id': technician_id,
            'target_partners': target_partner_ids,
        },
    )
    return result


# Backward-compatible alias
notify_all_partners_new_booking = notify_partners_new_booking


def notify_partner_assigned(job: JobCard, partner: Partner) -> None:
    if should_skip_duplicate_push(
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
    tokens = list(
        PartnerDeviceToken.objects.filter(partner=partner, is_active=True).values_list('fcm_token', flat=True)
    )
    send_push_to_tokens(tokens, title=title, body=body, data=data, collapse_key=f'booking_{job.id}')


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
    if should_skip_duplicate_push(job.id, PartnerNotification.NotificationType.BOOKING_CANCELLED):
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
    tokens = []
    for p in partners_qs:
        create_partner_notification(
            p,
            notification_type=PartnerNotification.NotificationType.BOOKING_CANCELLED,
            title=title,
            body=body,
            booking=job,
            data=data,
        )
        tokens.extend(
            PartnerDeviceToken.objects.filter(partner=p, is_active=True).values_list('fcm_token', flat=True)
        )
    send_push_to_tokens(tokens, title=title, body=body, data=data, collapse_key=f'cancel_{job.id}')
