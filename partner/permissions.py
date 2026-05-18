from rest_framework.permissions import BasePermission

from .utils import get_partner_from_token


class IsPartnerAuthenticated(BasePermission):
    """Valid partner JWT only (login, profile, approval status)."""

    message = 'Partner authentication required. Pass a valid Bearer token.'

    def has_permission(self, request, view):
        if getattr(request, 'partner', None):
            return True

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


class IsPartner(IsPartnerAuthenticated):
    """Partner with admin-approved app access (bookings, earnings, etc.)."""

    message = 'Your partner account is pending admin approval. Contact Pest Control 99 office.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        partner = request.partner
        if not partner.is_active:
            self.message = 'Your account has been deactivated. Contact admin.'
            return False
        if not partner.is_app_approved:
            return False
        return True


class IsPartnerAdmin(IsPartner):
    """Technician admin role with full partner app access."""

    message = 'Technician Admin role required.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.partner.role == 'technician_admin'
