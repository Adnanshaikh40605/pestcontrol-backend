from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.roles import can_access_blog_cms, is_blog_user, is_crm_operational_user


class IsBlogCMSUser(BasePermission):
    """Blog CMS: super_admin, admin, staff, and blog_user."""
    message = 'Permission denied'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return can_access_blog_cms(request.user)


class BlogUserNoDelete(BasePermission):
    """blog_user cannot delete posts (optional safety)."""
    message = 'Permission denied'

    def has_permission(self, request, view):
        if request.method == 'DELETE' and is_blog_user(request.user):
            return False
        return True


class IsBlogAdmin(BasePermission):
    """Legacy: staff/superuser full access; blog_user read via CMS user check."""
    message = 'Permission denied'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(
            request.user
            and request.user.is_authenticated
            and (is_crm_operational_user(request.user) or request.user.is_superuser)
        )


class IsAuthenticatedBlogEditor(BasePermission):
    """Requires authentication for write operations."""
    message = 'Authentication required to manage blog content.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and can_access_blog_cms(request.user))
