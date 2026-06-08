"""DRF permission classes for CRM vs Blog CMS access."""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .roles import (
    is_blog_user,
    is_crm_operational_user,
    can_access_blog_cms,
    get_user_role,
    ROLE_BLOG_USER,
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
)


class IsCRMOperationalUser(BasePermission):
    """
    CRM bookings, clients, payments, staff, etc.
    Blocks blog_user entirely.
    """
    message = 'Permission denied'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if is_blog_user(request.user):
            return False
        return is_crm_operational_user(request.user)


class IsSuperAdmin(BasePermission):
    message = 'Permission denied'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsBlogCMSUser(BasePermission):
    """Blog CMS — operational CRM users + blog_user."""
    message = 'Permission denied'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return can_access_blog_cms(request.user)


class IsPricingAdmin(BasePermission):
    """Super Admin and Admin only — staff/technicians use pricing-config for bookings."""
    message = 'Only Admin users can access Pricing Master.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if is_blog_user(request.user):
            return False
        role = get_user_role(request.user)
        return role in (ROLE_SUPER_ADMIN, ROLE_ADMIN)


class IsRemarkAdmin(BasePermission):
    """Admin/super_admin may edit or delete remarks; staff may only create."""
    message = 'Permission denied'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if is_blog_user(request.user):
            return False
        role = get_user_role(request.user)
        return role in (ROLE_SUPER_ADMIN, ROLE_ADMIN)


class BlogUserNoDelete(BasePermission):
    """Optional: blog_user cannot DELETE blogs."""
    message = 'Permission denied'

    def has_permission(self, request, view):
        if request.method == 'DELETE' and is_blog_user(request.user):
            return False
        return True
