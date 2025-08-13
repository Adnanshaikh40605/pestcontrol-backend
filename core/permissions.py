from rest_framework import permissions

class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    Non-admin users can only read objects.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Write permissions are only allowed to admin users.
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admin users to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Instance must have an attribute named `owner` or `user`.
        if hasattr(obj, 'owner'):
            return obj.owner == request.user or request.user.is_staff
        elif hasattr(obj, 'user'):
            return obj.user == request.user or request.user.is_staff
        
        # If the object doesn't have owner or user attribute, only admins can edit
        return request.user and request.user.is_staff


class AllowWebhookPost(permissions.BasePermission):
    """
    Custom permission to allow webhook POST requests without authentication.
    """
    
    def has_permission(self, request, view):
        # Allow unauthenticated POST requests to webhook endpoints
        if request.method == 'POST' and 'webhook' in request.path:
            return True
        
        # For all other requests, require authentication
        return request.user and request.user.is_authenticated