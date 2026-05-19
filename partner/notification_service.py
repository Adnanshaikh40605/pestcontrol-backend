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

    # One active token per partner — deactivate older devices after reinstall/login.
    PartnerDeviceToken.objects.filter(partner=partner, is_active=True).exclude(
        fcm_token=fcm_token
    ).update(is_active=False)

    logger.info(
        'FCM token registered partner=%s (%s) approved=%s device=%s',
        partner.id,
        partner.mobile,
        partner.is_app_approved,
        device_type,
    )
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


def approved_partner_ids(technician_id: int | None = None) -> list[int]:
    """Partner PKs that receive pool broadcast / in-app new-booking alerts."""
    qs = Partner.objects.filter(is_active=True, is_app_approved=True)
    target = _partner_ids_for_technician(technician_id)
    if target is not None:
        if not target:
            return []
        qs = qs.filter(pk__in=target)
    return list(qs.values_list('pk', flat=True))


def partners_with_tokens_outside_push_pool() -> list[dict[str, Any]]:
    """Active tokens whose partner is not approved — common cause of push_success=0."""
    out: list[dict[str, Any]] = []
    for dt in PartnerDeviceToken.objects.filter(is_active=True).select_related('partner'):
        p = dt.partner
        if p.is_active and p.is_app_approved:
            continue
        out.append(
            {
                'partner_id': p.id,
                'mobile': p.mobile,
                'full_name': p.full_name,
                'is_active': p.is_active,
                'is_app_approved': p.is_app_approved,
            }
        )
    return out


def active_tokens_for_partners(partner_ids: list[int] | None = None) -> list[str]:
    """
    FCM tokens for the given partner PKs.
    None = all approved active partners (same pool as send-to-app broadcast).
    """
    if partner_ids is None:
        partner_ids = approved_partner_ids(None)
    if not partner_ids:
        return []

    tokens: list[str] = []
    seen: set[str] = set()

    for raw in PartnerDeviceToken.objects.filter(
        is_active=True,
        partner_id__in=partner_ids,
    ).values_list('fcm_token', flat=True):
        t = (raw or '').strip()
        if t and t not in seen:
            seen.add(t)
            tokens.append(t)

    # Legacy fallback: Partner.fcm_token if device row missing.
    for raw in Partner.objects.filter(pk__in=partner_ids).values_list('fcm_token', flat=True):
        t = (raw or '').strip()
        if t and t not in seen:
            seen.add(t)
            tokens.append(t)

    return tokens


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

    partner_ids_for_push = approved_partner_ids(technician_id)
    partners_qs = Partner.objects.filter(pk__in=partner_ids_for_push)

    for partner in partners_qs:
        create_partner_notification(
            partner,
            notification_type=PartnerNotification.NotificationType.NEW_BOOKING,
            title=title,
            body=body,
            booking=job,
            data=data,
        )

    tokens = active_tokens_for_partners(partner_ids_for_push)
    excluded = partners_with_tokens_outside_push_pool()
    logger.info(
        'FCM job #%s: approved_partners=%s active_tokens=%s excluded_token_holders=%s',
        job.id,
        len(partner_ids_for_push),
        len(tokens),
        len(excluded),
    )
    if not tokens and excluded:
        logger.warning(
            'Job #%s: %s partner(s) have FCM tokens but are NOT approved — enable is_app_approved in Admin',
            job.id,
            len(excluded),
        )
    elif not tokens:
        logger.warning('No active FCM tokens for job #%s — partners must log in on the app', job.id)

    # notification + data: Android shows tray when app is background/killed.
    result = send_push_to_tokens(
        tokens,
        title=title,
        body=body,
        data=data,
        collapse_key=collapse_key,
        channel_id='pest99_booking_alerts_v4',
        sound='default',
        data_only=False,
    )
    result['skipped'] = False
    result['fcm_configured'] = is_fcm_configured()
    result['tokens_targeted'] = len(tokens)
    result['approved_partner_count'] = len(partner_ids_for_push)
    if not tokens and excluded:
        result['push_hint'] = (
            'FCM tokens exist on server but the partner account is not approved (is_app_approved=False). '
            'Approve the partner in Django Admin or CRM Technicians, then send again.'
        )
        result['unapproved_token_holders'] = excluded[:5]

    log_crm_partner_event(
        job,
        CrmPartnerEvent.EventType.BOOKING_SENT_TO_APP,
        f'Push sent to {len(tokens)} device(s)',
        {
            'fcm_success': result.get('success', 0),
            'fcm_failure': result.get('failure', 0),
            'technician_id': technician_id,
            'approved_partner_ids': partner_ids_for_push,
            'tokens_targeted': len(tokens),
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
