from rest_framework.permissions import BasePermission
from .utils import get_partner_from_token


class IsPartner(BasePermission):
    """
    Custom permission for Partner App users.
    Extracts and validates the JWT token from Authorization header.
    Sets request.partner for downstream use.
    """
    message = "Partner authentication required. Pass a valid Bearer token."

    def has_permission(self, request, view):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False

        token = auth_header.split(' ', 1)[1]
        try:
            partner = get_partner_from_token(token)
            request.partner = partner
            return True
        except Exception:
            return False


class IsPartnerAdmin(IsPartner):
    """
    Extends IsPartner, additionally requires technician_admin role.
    """
    message = "Technician Admin role required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.partner.role == 'technician_admin'
