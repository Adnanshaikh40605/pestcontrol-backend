"""Partner JWT auth — must run before SimpleJWT to avoid token type errors."""

from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .utils import get_partner_from_token


class PartnerJWTAuthentication(BaseAuthentication):
    """
    Validates custom Partner JWT on /api/partner/* routes.
    SimpleJWT expects Django-user tokens and raises 'Given token not valid for any token type'
    if it runs first on partner tokens.
    """

    def authenticate(self, request):
        path = request.path or ''
        if not path.startswith('/api/partner/'):
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return None

        try:
            partner = get_partner_from_token(token)
        except Exception as exc:
            raise AuthenticationFailed('Invalid or expired partner session. Please log in again.') from exc

        request.partner = partner
        return (AnonymousUser(), partner)
