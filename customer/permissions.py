from rest_framework.permissions import BasePermission

from .utils import get_customer_from_token


class IsCustomerAuthenticated(BasePermission):
    message = 'Customer authentication required. Pass a valid Bearer token.'

    def has_permission(self, request, view):
        if getattr(request, 'customer', None):
            return True

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False

        token = auth_header.split(' ', 1)[1]
        try:
            account = get_customer_from_token(token)
            request.customer = account
            return True
        except Exception:
            return False


class IsCustomer(IsCustomerAuthenticated):
    message = 'Your customer account is inactive. Contact support.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if not request.customer.is_active:
            return False
        return True
