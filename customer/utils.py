"""Customer JWT helpers — mirrors partner/utils.py."""
from __future__ import annotations

import datetime
import uuid

import jwt
from django.conf import settings

from .models import CustomerAccount, CustomerRevokedJti

SECRET_KEY = getattr(settings, 'SECRET_KEY', 'customer-app-secret')

CUSTOMER_ACCESS_LIFETIME = datetime.timedelta(days=7)
CUSTOMER_REFRESH_LIFETIME = datetime.timedelta(days=60)


class CustomerTokenError(Exception):
    """Invalid, expired, or revoked customer JWT."""


def generate_customer_tokens(account: CustomerAccount) -> dict:
    now = datetime.datetime.utcnow()
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_payload = {
        'customer_id': account.id,
        'mobile': account.mobile,
        'type': 'access',
        'jti': access_jti,
        'iat': now,
        'exp': now + CUSTOMER_ACCESS_LIFETIME,
        'aud': 'customer',
    }
    refresh_payload = {
        'customer_id': account.id,
        'type': 'refresh',
        'jti': refresh_jti,
        'iat': now,
        'exp': now + CUSTOMER_REFRESH_LIFETIME,
        'aud': 'customer',
    }

    return {
        'access': jwt.encode(access_payload, SECRET_KEY, algorithm='HS256'),
        'refresh': jwt.encode(refresh_payload, SECRET_KEY, algorithm='HS256'),
    }


def decode_customer_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=['HS256'],
            audience='customer',
        )
    except jwt.ExpiredSignatureError as exc:
        raise CustomerTokenError('Token has expired.') from exc
    except jwt.InvalidTokenError as exc:
        raise CustomerTokenError('Invalid token.') from exc


def get_customer_from_token(token: str) -> CustomerAccount:
    payload = decode_customer_token(token)
    if payload.get('type') != 'access':
        raise CustomerTokenError('Invalid token type.')
    if payload.get('aud') != 'customer':
        raise CustomerTokenError('Invalid token audience.')
    customer_id = payload.get('customer_id')
    if not customer_id:
        raise CustomerTokenError('Invalid token payload.')
    try:
        account = CustomerAccount.objects.select_related('client').get(id=customer_id)
    except CustomerAccount.DoesNotExist as exc:
        raise CustomerTokenError('Account not found.') from exc
    if not account.is_active:
        raise ValueError('Your account has been deactivated.')
    return account


def refresh_customer_tokens(refresh_token: str) -> dict:
    payload = decode_customer_token(refresh_token)
    if payload.get('type') != 'refresh':
        raise CustomerTokenError('Invalid token type.')
    if payload.get('aud') != 'customer':
        raise CustomerTokenError('Invalid token audience.')

    jti = payload.get('jti')
    if not jti:
        raise CustomerTokenError('Invalid token.')
    if CustomerRevokedJti.objects.filter(jti=jti).exists():
        raise CustomerTokenError('Token has been revoked.')

    customer_id = payload.get('customer_id')
    try:
        account = CustomerAccount.objects.get(id=customer_id, is_active=True)
    except CustomerAccount.DoesNotExist as exc:
        raise CustomerTokenError('Account not found or inactive.') from exc

    exp = payload.get('exp')
    if exp:
        expires_at = datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc)
        CustomerRevokedJti.objects.get_or_create(jti=jti, defaults={'expires_at': expires_at})

    return generate_customer_tokens(account)
