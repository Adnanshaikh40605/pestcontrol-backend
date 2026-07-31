"""Customer JWT auth — scoped to /api/customer/*."""
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .utils import get_customer_from_token


class CustomerJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        path = request.path or ''
        if not path.startswith('/api/customer/'):
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return None

        try:
            account = get_customer_from_token(token)
        except ValueError as exc:
            raise AuthenticationFailed(str(exc)) from exc
        except Exception as exc:
            raise AuthenticationFailed(
                'Invalid or expired customer session. Please log in again.'
            ) from exc

        request.customer = account
        return (AnonymousUser(), account)
