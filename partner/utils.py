import datetime
import uuid

import jwt
from django.conf import settings
from django.utils import timezone

from .models import Partner, PartnerRevokedJti

SECRET_KEY = getattr(settings, 'SECRET_KEY', 'partner-app-secret')

PARTNER_ACCESS_LIFETIME = datetime.timedelta(days=7)
PARTNER_REFRESH_LIFETIME = datetime.timedelta(days=60)


class PartnerTokenError(Exception):
    """Invalid, expired, or revoked partner JWT."""


def generate_partner_tokens(partner: Partner) -> dict:
    """Issue new access + refresh JWT pair with unique JTIs for rotation."""
    now = datetime.datetime.utcnow()
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_payload = {
        'partner_id': partner.id,
        'mobile': partner.mobile,
        'role': partner.role,
        'type': 'access',
        'jti': access_jti,
        'iat': now,
        'exp': now + PARTNER_ACCESS_LIFETIME,
    }

    refresh_payload = {
        'partner_id': partner.id,
        'type': 'refresh',
        'jti': refresh_jti,
        'iat': now,
        'exp': now + PARTNER_REFRESH_LIFETIME,
    }

    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm='HS256')

    return {
        'access': access_token,
        'refresh': refresh_token,
    }


def decode_partner_token(token: str) -> dict:
    """Decode and validate a partner JWT token. Returns payload or raises."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError as exc:
        raise PartnerTokenError('Token has expired.') from exc
    except jwt.InvalidTokenError as exc:
        raise PartnerTokenError('Invalid token.') from exc


def _revoke_refresh_jti(jti: str, exp_timestamp: int) -> None:
    expires_at = datetime.datetime.fromtimestamp(exp_timestamp, tz=datetime.timezone.utc)
    PartnerRevokedJti.objects.get_or_create(
        jti=jti,
        defaults={'expires_at': expires_at},
    )


def refresh_partner_tokens(refresh_token: str) -> dict:
    """
    Validate refresh token, rotate (revoke old refresh JTI), return new token pair.
    Rejects inactive/disabled partners.
    """
    payload = decode_partner_token(refresh_token)

    if payload.get('type') != 'refresh':
        raise PartnerTokenError('Invalid token type.')

    jti = payload.get('jti')
    if not jti:
        raise PartnerTokenError('Invalid refresh token.')

    if PartnerRevokedJti.objects.filter(jti=jti).exists():
        raise PartnerTokenError('Refresh token has been revoked.')

    partner_id = payload.get('partner_id')
    if not partner_id:
        raise PartnerTokenError('Invalid token payload.')

    try:
        partner = Partner.objects.get(id=partner_id)
    except Partner.DoesNotExist as exc:
        raise PartnerTokenError('Partner not found.') from exc

    if not partner.is_active:
        raise PartnerTokenError('Your account has been deactivated. Contact admin.')

    exp = payload.get('exp')
    if exp:
        _revoke_refresh_jti(jti, int(exp))

    return generate_partner_tokens(partner)


def get_partner_from_token(token: str) -> Partner:
    """Decode access token and fetch active Partner from DB."""
    payload = decode_partner_token(token)
    if payload.get('type') != 'access':
        raise ValueError('Invalid token: not an access token')
    partner_id = payload.get('partner_id')
    if not partner_id:
        raise ValueError('Invalid token: no partner_id')
    partner = Partner.objects.get(id=partner_id, is_active=True)
    return partner


def cleanup_expired_revoked_jtis() -> int:
    """Remove revoked JTI records past expiry (housekeeping)."""
    deleted, _ = PartnerRevokedJti.objects.filter(expires_at__lt=timezone.now()).delete()
    return deleted
