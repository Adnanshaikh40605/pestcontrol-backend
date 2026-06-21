from rest_framework.permissions import BasePermission

from core.permissions import IsCRMOperationalUser
from core.roles import ROLE_ADMIN, ROLE_SUPER_ADMIN, get_user_role


def is_mobile_tracking_admin(request) -> bool:
    """Partner technician_admin or CRM admin/super_admin."""
    partner = getattr(request, 'partner', None)
    if partner and partner.is_active and partner.role == 'technician_admin':
        return True
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and get_user_role(user) in {ROLE_SUPER_ADMIN, ROLE_ADMIN}:
        return True
    return False


class IsCRMTrackingViewer(BasePermission):
    """CRM users who can view staff tracking dashboards."""

    def has_permission(self, request, view):
        return IsCRMOperationalUser().has_permission(request, view)


class IsCRMTrackingAdmin(BasePermission):
    """Admins who can change tracking settings."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return get_user_role(request.user) in {ROLE_SUPER_ADMIN, ROLE_ADMIN}


class IsTrackedStaff(BasePermission):
    """Partner or CRM user with an active tracking profile."""

    def has_permission(self, request, view):
        from staff_tracking.identity import resolve_profile_from_request
        return resolve_profile_from_request(request) is not None


class IsPartnerOrCRMTrackingViewer(BasePermission):
    """Tracked staff (mobile) or CRM operational user (dashboard)."""

    def has_permission(self, request, view):
        if IsTrackedStaff().has_permission(request, view):
            return True
        return IsCRMTrackingViewer().has_permission(request, view)


class IsTrackingLiveViewer(BasePermission):
    """CRM staff or mobile Technician Admin — live map / all technicians."""

    def has_permission(self, request, view):
        if IsCRMTrackingViewer().has_permission(request, view):
            return True
        return is_mobile_tracking_admin(request)
