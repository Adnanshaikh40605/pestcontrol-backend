"""Resolve tracking profiles from Partner, CRM User, or Technician."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from core.models import Technician
from core.staff_partner_sync import normalize_mobile
from partner.models import Partner

from .models import TrackingProfile


def get_or_create_profile(
    technician: Technician,
    *,
    partner: Partner | None = None,
    user=None,
) -> TrackingProfile:
    profile, created = TrackingProfile.objects.get_or_create(
        technician=technician,
        defaults={
            'partner': partner,
            'user': user,
        },
    )
    if not created:
        updates = []
        if partner and profile.partner_id != partner.id:
            profile.partner = partner
            updates.append('partner')
        if user and profile.user_id != user.id:
            profile.user = user
            updates.append('user')
        if updates:
            profile.save(update_fields=updates + ['updated_at'])
    return profile


def resolve_profile_from_partner(partner: Partner) -> TrackingProfile | None:
    if not partner or not partner.is_active:
        return None
    technician = partner.core_technician
    if technician is None:
        technician = Technician.objects.filter(mobile=partner.mobile, is_active=True).first()
        if technician and partner.core_technician_id != technician.id:
            partner.core_technician = technician
            partner.save(update_fields=['core_technician', 'updated_at'])
    if technician is None:
        return None
    return get_or_create_profile(technician, partner=partner)


def resolve_profile_from_user(user) -> TrackingProfile | None:
    if not user or not user.is_authenticated:
        return None
    mobile = normalize_mobile(user.username)
    if not mobile:
        return None
    technician = Technician.objects.filter(mobile=mobile, is_active=True).first()
    if technician is None:
        return None
    partner = Partner.objects.filter(mobile=mobile).first()
    return get_or_create_profile(technician, partner=partner, user=user)


def resolve_profile_from_request(request) -> TrackingProfile | None:
    partner = getattr(request, 'partner', None)
    if partner is not None:
        return resolve_profile_from_partner(partner)
    if request.user and request.user.is_authenticated:
        return resolve_profile_from_user(request.user)
    return None


def ensure_consent(profile: TrackingProfile, ip_address: str | None = None):
    from .models import TrackingConsent
    TrackingConsent.objects.get_or_create(
        profile=profile,
        defaults={'ip_address': ip_address},
    )
