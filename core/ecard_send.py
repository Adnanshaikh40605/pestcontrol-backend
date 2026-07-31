"""
Pest e-Card WhatsApp send ledger helpers.

Normalize mobiles to 10 digits and look up / record template sends.
"""
from __future__ import annotations

import re

from django.utils import timezone


ECARD_DEFAULT_TEMPLATE = 'pestecardaadsd'


def normalize_ecard_mobile(raw: str | None) -> str:
    """
    Return a 10-digit Indian mobile, or '' if invalid.

    Accepts: 9372792693, 919372792693, +91 93727 92693, 09372792693
    """
    digits = re.sub(r'\D', '', str(raw or ''))
    if digits.startswith('0'):
        digits = digits.lstrip('0')
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    if len(digits) == 10 and digits.isdigit():
        return digits
    return ''


def staff_display_name(user) -> str:
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    full = (user.get_full_name() or '').strip()
    if full:
        return full
    return (getattr(user, 'username', '') or '').strip()


def get_ecard_send_for_mobile(mobile: str):
    from core.models import ECardWhatsAppSend

    normalized = normalize_ecard_mobile(mobile)
    if not normalized:
        return None
    return ECardWhatsAppSend.objects.filter(mobile=normalized).first()


def mark_ecard_sent(
    *,
    mobile: str,
    user=None,
    sent_by: str = '',
    customer_name: str = '',
    source: str = '',
    template_name: str = ECARD_DEFAULT_TEMPLATE,
):
    """
    Create or refresh the send ledger row for this mobile.
    Idempotent: first send wins for already_sent; later calls update metadata.
    """
    from core.models import ECardWhatsAppSend

    normalized = normalize_ecard_mobile(mobile)
    if not normalized:
        raise ValueError('Enter a valid 10-digit mobile number.')

    display = (sent_by or '').strip() or staff_display_name(user)
    now = timezone.now()
    row, created = ECardWhatsAppSend.objects.get_or_create(
        mobile=normalized,
        defaults={
            'template_name': template_name or ECARD_DEFAULT_TEMPLATE,
            'customer_name': (customer_name or '').strip(),
            'sent_by': display,
            'sent_by_user': user if user and getattr(user, 'is_authenticated', False) else None,
            'sent_at': now,
            'source': (source or '').strip()[:40],
        },
    )
    if not created:
        # Keep original sent_at / first sender for "already sent" messaging.
        # Only fill empty optional fields.
        update_fields = []
        if customer_name and not row.customer_name:
            row.customer_name = customer_name.strip()
            update_fields.append('customer_name')
        if source and not row.source:
            row.source = source.strip()[:40]
            update_fields.append('source')
        if update_fields:
            row.save(update_fields=update_fields + ['updated_at'])
    return row, created
