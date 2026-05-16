from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsBlogAdmin(BasePermission):
    """
    Allow full access to staff/superusers; read-only for others.
    """
    message = "You must be a staff member to perform this action."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        ))


class IsAuthenticatedBlogEditor(BasePermission):
    """
    Requires authentication for all write operations.
    Any authenticated user can create/edit blogs (fine-grained control via view logic).
    """
    message = "Authentication required to manage blog content."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
