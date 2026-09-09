"""
Read helpers for a partner's work status, which lives on the linked
core.Technician as `presence_status` (Active / On Leave / Suspended).

The app used to be able to write this field via an Online/Offline toggle, and
the job lifecycle overwrote it with busy/on_service. Both are gone: the status
is a desk decision now, so this module only reads it and turns it into the
payload the app renders.
"""
from __future__ import annotations

from django.utils import timezone

from core.models import Technician
from partner.services import PartnerBookingError


# Message shown to the technician for each status that stops work reaching
# them. Keyed by the stored value so the app and CRM never drift.
UNAVAILABLE_MESSAGES = {
    Technician.PresenceStatus.SUSPENDED: 'Your account is suspended.',
    Technician.PresenceStatus.ON_LEAVE: 'You are marked as on leave.',
}


def resolve_technician(partner):
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        raise PartnerBookingError(
            'Your profile is not linked to a CRM technician record. Contact admin.',
            code='no_technician_link',
        )
    return tech


def partner_presence_status(partner) -> str | None:
    tech = getattr(partner, 'core_technician', None)
    return tech.presence_status if tech else None


def is_partner_suspended(partner) -> bool:
    tech = getattr(partner, 'core_technician', None)
    return bool(tech and tech.is_suspended)


def is_partner_on_leave(partner) -> bool:
    tech = getattr(partner, 'core_technician', None)
    return bool(tech and tech.is_on_leave)


def is_partner_unavailable(partner) -> bool:
    """True when the desk has marked this technician on leave or suspended."""
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        return False
    return tech.presence_status in Technician.UNAVAILABLE_PRESENCE


def unavailable_reason(partner) -> str:
    """Sentence to show the technician, empty when they are available."""
    tech = getattr(partner, 'core_technician', None)
    if not tech or tech.presence_status not in Technician.UNAVAILABLE_PRESENCE:
        return ''
    base = UNAVAILABLE_MESSAGES.get(tech.presence_status, 'You are not available for work.')
    detail = (tech.suspend_reason or '').strip()
    return f'{base} {detail}' if detail else f'{base} Contact CRM admin.'


def ensure_partner_available(partner) -> None:
    """
    Guard for taking on NEW work: accepting a job, or seeing the pool.

    Raises for both on leave and suspended.
    """
    tech = getattr(partner, 'core_technician', None)
    if not tech or tech.presence_status not in Technician.UNAVAILABLE_PRESENCE:
        return
    raise PartnerBookingError(
        unavailable_reason(partner),
        code='suspended' if tech.is_suspended else 'on_leave',
    )


def ensure_partner_not_suspended(partner) -> None:
    """
    Guard for continuing work already in hand: starting, completing.

    Only suspension blocks here. Leave stops new jobs reaching a technician,
    but it must not strand a booking they already accepted — otherwise marking
    someone on leave mid-job leaves that job unfinishable.
    """
    tech = getattr(partner, 'core_technician', None)
    if not tech or not tech.is_suspended:
        return
    raise PartnerBookingError(unavailable_reason(partner), code='suspended')


def touch_partner_activity(partner) -> None:
    """
    Record that the technician did something in the app.

    Accept/start/complete used to refresh `last_active` as a side effect of
    writing presence. Presence no longer moves, but auto-suspend still keys off
    `last_active`, so working a job has to keep counting as activity.
    """
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        return
    tech.last_active = timezone.now()
    tech.save(update_fields=['last_active', 'updated_at'])


def presence_payload(partner) -> dict:
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        return {
            'presence_status': None,
            'presence_label': '',
            'last_active': None,
            'is_available': False,
            'is_suspended': False,
            'is_on_leave': False,
            'unavailable_reason': '',
            'suspend_reason': '',
            'technician_linked': False,
        }
    return {
        'presence_status': tech.presence_status,
        'presence_label': tech.get_presence_status_display(),
        'last_active': tech.last_active.isoformat() if tech.last_active else None,
        'is_available': tech.is_available_for_work,
        'is_suspended': tech.is_suspended,
        'is_on_leave': tech.is_on_leave,
        'unavailable_reason': unavailable_reason(partner),
        'suspend_reason': tech.suspend_reason or '',
        'technician_linked': True,
        'technician_type': tech.technician_type,
    }
