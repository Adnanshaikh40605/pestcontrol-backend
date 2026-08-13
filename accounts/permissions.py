from rest_framework.permissions import BasePermission, SAFE_METHODS


class AccountsAccess(BasePermission):
    """Staff users can view; manage requires is_staff (CRM). Superusers always allowed."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return False


class AccountsManage(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return user.is_staff or user.is_superuser
        return user.is_staff or user.is_superuser
