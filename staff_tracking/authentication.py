"""Dual JWT auth for staff tracking — Partner mobile tokens + CRM SimpleJWT."""

from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from partner.utils import PartnerTokenError, get_partner_from_token


class StaffTrackingAuthentication(BaseAuthentication):
    """
    Accept Partner JWT or CRM SimpleJWT on /api/staff-tracking/* routes.
    Sets request.partner and/or request.user plus request.tracking_auth_type.
    """

    def authenticate(self, request):
        path = request.path or ''
        if not path.startswith('/api/staff-tracking/'):
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return None

        # Partner JWT (custom payload with partner_id + type=access)
        try:
            partner = get_partner_from_token(token)
            request.partner = partner
            request.tracking_auth_type = 'partner'
            return (AnonymousUser(), partner)
        except (PartnerTokenError, ValueError):
            pass

        # CRM SimpleJWT
        jwt_auth = JWTAuthentication()
        try:
            result = jwt_auth.authenticate(request)
        except InvalidToken as exc:
            raise AuthenticationFailed('Invalid or expired session. Please log in again.') from exc

        if result is None:
            return None

        user, validated_token = result
        request.tracking_auth_type = 'crm'
        return (user, validated_token)
