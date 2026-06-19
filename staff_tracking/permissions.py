from rest_framework.permissions import BasePermission

from core.permissions import IsCRMOperationalUser
from core.roles import ROLE_ADMIN, ROLE_SUPER_ADMIN, get_user_role


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
