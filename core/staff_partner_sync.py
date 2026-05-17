"""Link CRM Staff (Technician role) ↔ core.Technician ↔ Partner (Flutter app)."""

from __future__ import annotations

import re

from django.contrib.auth.hashers import identify_hasher
from rest_framework import serializers

from core.models import Technician
from core.roles import ROLE_TECHNICIAN, get_user_role
from partner.models import Partner


def normalize_mobile(value: str) -> str:
    """10-digit Indian mobile used consistently across User, Technician, Partner."""
    digits = re.sub(r'\D', '', value or '')
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def _partner_has_usable_password(partner: Partner) -> bool:
    if not partner.password:
        return False
    try:
        identify_hasher(partner.password)
        return True
    except ValueError:
        return False


def partner_link_status(user) -> dict:
    """Read-only status for CRM staff UI."""
    role = get_user_role(user)
    if role != ROLE_TECHNICIAN:
        return {
            'partner_app_ready': False,
            'partner_id': None,
            'technician_id': None,
        }

    mobile = normalize_mobile(user.username)
    tech = Technician.objects.filter(mobile=mobile).first()
    partner = Partner.objects.filter(mobile=mobile).select_related('core_technician').first()
    linked = bool(
        tech
        and partner
        and partner.is_active
        and partner.core_technician_id == tech.id
        and _partner_has_usable_password(partner)
    )
    return {
        'partner_app_ready': linked,
        'partner_id': partner.id if partner else None,
        'technician_id': tech.id if tech else None,
    }


def sync_technician_partner_account(
    user,
    role_label: str,
    password: str | None = None,
    *,
    old_mobile: str | None = None,
) -> None:
    """
    Technician staff type → CRM Technician row + Partner app login (same mobile/password).
    Flutter app authenticates via Partner table, not Django User.
    """
    if role_label != 'Technician':
        return

    mobile = normalize_mobile(user.username)
    name = (user.first_name or '').strip() or mobile

    if not mobile or len(mobile) != 10:
        raise serializers.ValidationError(
            {'mobile': 'Enter a valid 10-digit mobile number for technician / partner app login.'}
        )

    if old_mobile:
        prev = normalize_mobile(old_mobile)
        if prev and prev != mobile:
            Technician.objects.filter(mobile=prev).update(mobile=mobile, name=name)
            Partner.objects.filter(mobile=prev).update(mobile=mobile, full_name=name)

    tech, _ = Technician.objects.update_or_create(
        mobile=mobile,
        defaults={'name': name, 'is_active': user.is_active},
    )

    partner = Partner.objects.filter(mobile=mobile).first()
    if partner is None:
        partner = Partner(
            full_name=name,
            mobile=mobile,
            role=Partner.Role.TECHNICIAN,
        )
    else:
        partner.full_name = name
        partner.role = Partner.Role.TECHNICIAN

    partner.core_technician = tech
    partner.is_active = user.is_active

    if password:
        partner.set_password(password)
    elif not _partner_has_usable_password(partner):
        raise serializers.ValidationError(
            {
                'password': (
                    'Password is required to enable Partner app login for this technician.'
                )
            }
        )

    partner.save()
