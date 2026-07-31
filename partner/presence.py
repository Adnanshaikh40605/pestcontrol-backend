"""
Partner presence helpers (sync to linked core.Technician).
"""
from __future__ import annotations

from django.utils import timezone

from core.models import Technician
from partner.services import PartnerBookingError


ALLOWED_SELF_PRESENCE = {
    Technician.PresenceStatus.ONLINE,
    Technician.PresenceStatus.OFFLINE,
}

# System statuses the app must not overwrite via the Online/Offline toggle
SYSTEM_BUSY_STATUSES = {
    Technician.PresenceStatus.BUSY,
    Technician.PresenceStatus.ON_SERVICE,
    Technician.PresenceStatus.ON_LEAVE,
}


def resolve_technician(partner):
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        raise PartnerBookingError(
            'Your profile is not linked to a CRM technician record. Contact admin.',
            code='no_technician_link',
        )
    return tech


def is_partner_suspended(partner) -> bool:
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        return False
    return tech.presence_status == Technician.PresenceStatus.SUSPENDED


def ensure_partner_not_suspended(partner) -> None:
    tech = getattr(partner, 'core_technician', None)
    if tech and tech.presence_status == Technician.PresenceStatus.SUSPENDED:
        reason = (tech.suspend_reason or '').strip() or 'Contact CRM admin.'
        raise PartnerBookingError(
            f'Your account is suspended. {reason}',
            code='suspended',
        )


def set_partner_presence(partner, presence_status: str, *, allow_system: bool = False) -> Technician:
    tech = resolve_technician(partner)
    if tech.presence_status == Technician.PresenceStatus.SUSPENDED and not allow_system:
        if presence_status != Technician.PresenceStatus.SUSPENDED:
            raise PartnerBookingError(
                'Suspended accounts cannot change presence. Contact CRM admin.',
                code='suspended',
            )
    # Protect in-job / leave states from accidental Online/Offline toggle
    if (
        not allow_system
        and tech.presence_status in SYSTEM_BUSY_STATUSES
        and presence_status in ALLOWED_SELF_PRESENCE
    ):
        raise PartnerBookingError(
            f'Cannot switch availability while status is "{tech.presence_status}". '
            'Finish or leave the current job first.',
            code='presence_locked',
        )
    if not allow_system and presence_status not in ALLOWED_SELF_PRESENCE:
        raise PartnerBookingError(
            'You can only set Online or Offline from the app.',
            code='invalid_presence',
        )
    if presence_status not in dict(Technician.PresenceStatus.choices):
        raise PartnerBookingError('Invalid presence status.', code='invalid_presence')

    tech.presence_status = presence_status
    tech.last_active = timezone.now()
    tech.save(update_fields=['presence_status', 'last_active', 'updated_at'])
    return tech


def presence_payload(partner) -> dict:
    tech = getattr(partner, 'core_technician', None)
    if not tech:
        return {
            'presence_status': None,
            'last_active': None,
            'is_suspended': False,
            'suspend_reason': '',
            'technician_linked': False,
        }
    return {
        'presence_status': tech.presence_status,
        'last_active': tech.last_active.isoformat() if tech.last_active else None,
        'is_suspended': tech.presence_status == Technician.PresenceStatus.SUSPENDED,
        'suspend_reason': tech.suspend_reason or '',
        'technician_linked': True,
        'technician_type': tech.technician_type,
    }
