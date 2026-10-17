"""Technician app forgot-password: WhatsApp OTP, then a new password."""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.staff_partner_sync import normalize_mobile

from .models import Partner, PartnerOTPChallenge
from .serializers import PartnerPasswordOtpSerializer, PartnerPasswordResetSerializer
from .views_base import PartnerPublicAPIView

logger = logging.getLogger(__name__)

MAX_OTP_ATTEMPTS = 5


def _generate_otp() -> str:
    fixed = getattr(settings, 'CUSTOMER_OTP_FIXED', None)
    if fixed:
        return str(fixed).zfill(4)[:4]
    if settings.DEBUG:
        return '1234'
    return f'{secrets.randbelow(10000):04d}'


def _send_whatsapp_otp(mobile: str, otp: str, full_name: str) -> str:
    if settings.DEBUG:
        return 'debug_fixed'
    try:
        import threading

        from core.whatsflow_pc99 import notify_customer_otp

        wait_seconds = float(getattr(settings, 'CUSTOMER_OTP_WHATSAPP_WAIT_SECONDS', 6))
        box: dict = {'sent': False}

        def _deliver() -> None:
            box['sent'] = bool(notify_customer_otp(
                mobile=mobile,
                otp=otp,
                purpose='password_reset',
                customer_name=full_name or None,
                request_timeout=min(5.0, max(2.0, wait_seconds)),
            ))

        worker = threading.Thread(target=_deliver, daemon=True, name=f'partner-otp-{mobile[-4:]}')
        worker.start()
        worker.join(timeout=max(1.0, wait_seconds))
        return 'whatsapp' if box['sent'] else 'queued'
    except Exception:
        logger.exception('Partner password OTP WhatsApp failed mobile=%s', mobile)
        return 'pending_channel'


class PasswordOtpAPIView(PartnerPublicAPIView):
    """POST /api/partner/password/otp/ — send a reset OTP to a registered technician."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PartnerPasswordOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        mobile = serializer.validated_data['mobile']
        partner = Partner.objects.filter(mobile=mobile).first()
        if partner is None:
            return Response(
                {'error': 'No account found with this mobile number.', 'code': 'not_registered'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not partner.is_active:
            return Response(
                {'error': 'Your account has been deactivated. Contact admin.', 'code': 'inactive'},
                status=status.HTTP_403_FORBIDDEN,
            )

        purpose = PartnerOTPChallenge.PURPOSE_PASSWORD_RESET
        max_per_hour = int(getattr(settings, 'PARTNER_PASSWORD_OTP_MAX_PER_HOUR', 5))
        window_seconds = int(getattr(settings, 'PARTNER_PASSWORD_OTP_WINDOW_SECONDS', 3600))
        if max_per_hour > 0 and window_seconds > 0:
            since = timezone.now() - timedelta(seconds=window_seconds)
            recent = PartnerOTPChallenge.objects.filter(
                mobile=mobile,
                purpose=purpose,
                created_at__gte=since,
            )
            if recent.count() >= max_per_hour:
                return Response(
                    {
                        'error': (
                            f'You can request up to {max_per_hour} OTPs per hour. '
                            'Please try again later.'
                        ),
                        'code': 'otp_hourly_limit',
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        otp = _generate_otp()
        ttl = int(getattr(settings, 'CUSTOMER_OTP_TTL_SECONDS', 300))
        PartnerOTPChallenge.objects.filter(
            mobile=mobile,
            purpose=purpose,
            consumed_at__isnull=True,
        ).update(consumed_at=timezone.now())
        challenge = PartnerOTPChallenge(
            mobile=mobile,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(seconds=ttl),
        )
        challenge.set_otp(otp)
        challenge.save()

        if settings.DEBUG:
            logger.info('Partner password OTP mobile=%s otp=%s', mobile, otp)
        else:
            logger.info('Partner password OTP generated mobile=%s', mobile)

        delivery = _send_whatsapp_otp(mobile, otp, partner.full_name)
        payload = {
            'message': 'OTP sent to your WhatsApp number.',
            'mobile': mobile,
            'expires_in': ttl,
            'delivery': delivery,
        }
        if settings.DEBUG:
            payload['dev_otp'] = otp
        return Response(payload)


class PasswordResetAPIView(PartnerPublicAPIView):
    """POST /api/partner/password/reset/ — set a new password after the OTP matches."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PartnerPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        mobile = normalize_mobile(serializer.validated_data['mobile'])
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        purpose = PartnerOTPChallenge.PURPOSE_PASSWORD_RESET

        partner = Partner.objects.filter(mobile=mobile).first()
        if partner is None:
            return Response(
                {'error': 'No account found with this mobile number.', 'code': 'not_registered'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not partner.is_active:
            return Response(
                {'error': 'Your account has been deactivated. Contact admin.', 'code': 'inactive'},
                status=status.HTTP_403_FORBIDDEN,
            )

        challenge = (
            PartnerOTPChallenge.objects.filter(
                mobile=mobile,
                purpose=purpose,
                consumed_at__isnull=True,
            )
            .order_by('-created_at')
            .first()
        )
        if challenge is None:
            return Response(
                {'error': 'OTP expired or not found. Please request a new OTP.', 'code': 'otp_missing'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if challenge.expires_at <= timezone.now():
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=['consumed_at'])
            return Response(
                {'error': 'OTP expired. Please request a new OTP.', 'code': 'otp_expired'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if challenge.attempts >= MAX_OTP_ATTEMPTS:
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=['consumed_at'])
            return Response(
                {'error': 'Too many incorrect attempts. Request a new OTP.', 'code': 'otp_locked'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not challenge.check_otp(otp):
            challenge.attempts += 1
            if challenge.attempts >= MAX_OTP_ATTEMPTS:
                challenge.consumed_at = timezone.now()
            challenge.save(update_fields=['attempts', 'consumed_at'])
            return Response(
                {'error': 'Invalid OTP. Please try again.', 'code': 'otp_invalid'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        challenge.consumed_at = timezone.now()
        challenge.save(update_fields=['consumed_at'])
        partner.set_password(new_password)
        partner.save(update_fields=['password', 'updated_at'])
        return Response({'message': 'Password updated. You can log in with the new password.'})
