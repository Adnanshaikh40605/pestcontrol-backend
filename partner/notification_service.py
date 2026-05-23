"""
Partner push (FCM) + in-app notification records + CRM event log.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
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


def _partner_ids_for_technician(technician_id: int | None) -> list[int] | None:
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
        token_row = existing
    else:
        token_row = PartnerDeviceToken.objects.create(
            partner=partner,
            fcm_token=fcm_token,
            device_type=device_type or PartnerDeviceToken.DeviceType.ANDROID,
            is_active=True,
        )

    PartnerDeviceToken.objects.filter(partner=partner, is_active=True).exclude(
        fcm_token=fcm_token
    ).update(is_active=False)

    logger.info('FCM token registered for partner %s', partner.id)
    return token_row


def deactivate_device_token(partner: Partner, fcm_token: str | None = None) -> int:
    qs = PartnerDeviceToken.objects.filter(partner=partner, is_active=True)
    if fcm_token:
        qs = qs.filter(fcm_token=fcm_token.strip())
    return qs.update(is_active=False)


def active_tokens_for_partners(partner_ids: list[int] | None = None) -> list[str]:
    qs = PartnerDeviceToken.objects.filter(is_active=True, partner__is_active=True, partner__is_app_approved=True)
    if partner_ids is not None:
        qs = qs.filter(partner_id__in=partner_ids)
    return list(qs.values_list('fcm_token', flat=True))


def partners_with_tokens_outside_push_pool() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for dt in PartnerDeviceToken.objects.filter(is_active=True).select_related('partner'):
        p = dt.partner
        if p.is_active and p.is_app_approved:
            continue
        out.append({
            'partner_id': p.id,
            'partner_name': p.full_name,
            'is_app_approved': p.is_app_approved,
            'is_active': p.is_active,
        })
    return out


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
    """In-app + FCM when CRM sends a booking to the partner app."""
    if not force and should_skip_duplicate_push(
        job.id,
        PartnerNotification.NotificationType.NEW_BOOKING,
        technician_id,
    ):
        logger.info('Skipping duplicate push for job #%s', job.id)
        return {
            'skipped': True,
            'partners_notified': 0,
            'approved_partner_count': 0,
            'fcm_configured': is_fcm_configured(),
            'push_success': 0,
            'push_failure': 0,
            'tokens_targeted': 0,
        }

    title = 'New Booking Available'
    body = _booking_subtitle(job)
    data = {
        'type': PartnerNotification.NotificationType.NEW_BOOKING,
        'booking_id': str(job.id),
        'job_code': job.code or '',
    }
    collapse_key = f'booking_{job.id}'

    partner_ids = approved_partner_ids(technician_id)
    partners_qs = Partner.objects.filter(pk__in=partner_ids)

    for partner in partners_qs:
        if not force and should_skip_duplicate_notify(
            job.id,
            PartnerNotification.NotificationType.NEW_BOOKING,
            partner_id=partner.id,
        ):
            continue
        create_partner_notification(
            partner,
            notification_type=PartnerNotification.NotificationType.NEW_BOOKING,
            title=title,
            body=body,
            booking=job,
            data=data,
        )

    tokens = active_tokens_for_partners(partner_ids)
    excluded = partners_with_tokens_outside_push_pool()
    if not tokens and excluded:
        logger.warning(
            'FCM job #%s: tokens exist but partners not approved: %s',
            job.id,
            excluded[:3],
        )

    push_result = send_push_to_tokens(
        tokens,
        title=title,
        body=body,
        data=data,
        collapse_key=collapse_key,
        data_only=True,
    )

    log_crm_partner_event(
        job,
        CrmPartnerEvent.EventType.BOOKING_SENT_TO_APP,
        f'Push sent to {len(tokens)} device(s)',
        {
            'fcm_success': push_result.get('success', 0),
            'fcm_failure': push_result.get('failure', 0),
            'technician_id': technician_id,
            'approved_partner_ids': partner_ids,
            'tokens_targeted': len(tokens),
        },
    )

    result = {
        'skipped': False,
        'partners_notified': len(partner_ids),
        'approved_partner_count': len(partner_ids),
        'fcm_configured': is_fcm_configured(),
        'push_success': push_result.get('success', 0),
        'push_failure': push_result.get('failure', 0),
        'tokens_targeted': len(tokens),
    }
    if not tokens and excluded:
        result['push_hint'] = (
            'FCM tokens exist but partner is not approved (is_app_approved=False). '
            'Approve in CRM Technicians, then send again.'
        )
        result['unapproved_token_holders'] = excluded[:5]
    return result


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
    tokens = active_tokens_for_partners([partner.id])
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
    partner_ids = list(partners_qs.values_list('pk', flat=True))
    for p in partners_qs:
        create_partner_notification(
            p,
            notification_type=PartnerNotification.NotificationType.BOOKING_CANCELLED,
            title=title,
            body=body,
            booking=job,
            data=data,
        )
    tokens = active_tokens_for_partners(partner_ids)
    send_push_to_tokens(tokens, title=title, body=body, data=data, collapse_key=f'cancel_{job.id}')
