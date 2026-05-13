import jwt
import datetime
from django.conf import settings
from .models import Partner


SECRET_KEY = getattr(settings, 'SECRET_KEY', 'partner-app-secret')


def generate_partner_tokens(partner: Partner) -> dict:
    """
    Generate JWT access and refresh tokens for a Partner.
    Using a simple manual JWT since Partner is not a Django User model.
    """
    now = datetime.datetime.utcnow()

    access_payload = {
        'partner_id': partner.id,
        'mobile': partner.mobile,
        'role': partner.role,
        'type': 'access',
        'iat': now,
        'exp': now + datetime.timedelta(days=30),  # 30 days access
    }

    refresh_payload = {
        'partner_id': partner.id,
        'type': 'refresh',
        'iat': now,
        'exp': now + datetime.timedelta(days=90),  # 90 days refresh
    }

    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm='HS256')

    return {
        'access': access_token,
        'refresh': refresh_token,
    }


def decode_partner_token(token: str) -> dict:
    """Decode and validate a partner JWT token. Returns payload or raises exception."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    return payload


def get_partner_from_token(token: str) -> Partner:
    """Decode token and fetch Partner from DB."""
    payload = decode_partner_token(token)
    partner_id = payload.get('partner_id')
    if not partner_id:
        raise ValueError("Invalid token: no partner_id")
    partner = Partner.objects.get(id=partner_id, is_active=True)
    return partner
