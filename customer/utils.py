"""Customer JWT helpers — mirrors partner/utils.py."""
from __future__ import annotations

import datetime
import uuid

import jwt
from django.conf import settings
from django.core.cache import cache

from .models import CustomerAccount, CustomerRevokedJti

SECRET_KEY = getattr(settings, 'SECRET_KEY', 'customer-app-secret')

CUSTOMER_ACCESS_LIFETIME = datetime.timedelta(days=7)
CUSTOMER_REFRESH_LIFETIME = datetime.timedelta(days=60)

WEBSITE_BOOKING_TOKEN_AUD = 'website_booking_otp'
_WEBSITE_BOOKING_CACHE_PREFIX = 'website_booking_verified:'


class CustomerTokenError(Exception):
    """Invalid, expired, or revoked customer JWT."""


class WebsiteBookingVerificationError(Exception):
    """Invalid, expired, or already-used website booking OTP verification token."""

    def __init__(self, message: str, code: str = 'otp_verification_invalid'):
        super().__init__(message)
        self.message = message
        self.code = code


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


def _website_booking_verification_ttl() -> int:
    return int(getattr(settings, 'WEBSITE_BOOKING_VERIFICATION_TTL_SECONDS', 600))


def issue_website_booking_verification_token(mobile: str) -> tuple[str, int]:
    """
    Issue a short-lived, one-time JWT proving mobile OTP was verified for website booking.
    Returns (token, expires_in_seconds).
    """
    ttl = _website_booking_verification_ttl()
    now = datetime.datetime.utcnow()
    jti = str(uuid.uuid4())
    payload = {
        'mobile': mobile,
        'type': 'website_booking_verification',
        'jti': jti,
        'iat': now,
        'exp': now + datetime.timedelta(seconds=ttl),
        'aud': WEBSITE_BOOKING_TOKEN_AUD,
    }
    cache.set(f'{_WEBSITE_BOOKING_CACHE_PREFIX}{jti}', mobile, timeout=ttl)
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token, ttl


def consume_website_booking_verification_token(token: str, mobile: str) -> None:
    """
    Validate verification token matches mobile and consume it (one-time use).
    Raises WebsiteBookingVerificationError on failure.
    """
    if not token or not str(token).strip():
        raise WebsiteBookingVerificationError(
            'Mobile OTP verification is required before booking.',
            code='otp_verification_required',
        )
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=['HS256'],
            audience=WEBSITE_BOOKING_TOKEN_AUD,
        )
    except jwt.ExpiredSignatureError as exc:
        raise WebsiteBookingVerificationError(
            'OTP verification expired. Please verify again.',
            code='otp_verification_expired',
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise WebsiteBookingVerificationError(
            'Invalid OTP verification. Please verify again.',
            code='otp_verification_invalid',
        ) from exc

    if payload.get('type') != 'website_booking_verification':
        raise WebsiteBookingVerificationError(
            'Invalid OTP verification. Please verify again.',
            code='otp_verification_invalid',
        )
    token_mobile = str(payload.get('mobile') or '')
    if token_mobile != mobile:
        raise WebsiteBookingVerificationError(
            'OTP was verified for a different mobile number.',
            code='otp_verification_mobile_mismatch',
        )
    jti = payload.get('jti')
    if not jti:
        raise WebsiteBookingVerificationError(
            'Invalid OTP verification. Please verify again.',
            code='otp_verification_invalid',
        )
    cache_key = f'{_WEBSITE_BOOKING_CACHE_PREFIX}{jti}'
    cached_mobile = cache.get(cache_key)
    if cached_mobile is None:
        raise WebsiteBookingVerificationError(
            'OTP verification already used or expired. Please verify again.',
            code='otp_verification_used',
        )
    if str(cached_mobile) != mobile:
        raise WebsiteBookingVerificationError(
            'Invalid OTP verification. Please verify again.',
            code='otp_verification_invalid',
        )
    cache.delete(cache_key)
