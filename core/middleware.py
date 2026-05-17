"""API middleware — enforce blog_user route isolation at the HTTP layer."""

import logging

from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

from .roles import is_blog_user, ROLE_BLOG_USER

logger = logging.getLogger(__name__)

# Paths blog_user may call (prefix match unless noted)
BLOG_USER_ALLOWED_PREFIXES = (
    '/api/token/',
    '/api/blogs/',
    '/api/v1/health/',
    '/health',
)

BLOG_USER_ALLOWED_EXACT = (
    '/health/',
    '/',
)


def _path_allowed_for_blog_user(path: str) -> bool:
    if path in BLOG_USER_ALLOWED_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in BLOG_USER_ALLOWED_PREFIXES)


class BlogUserAPIRestrictionMiddleware:
    """
    After JWT resolution, block blog_user from all non-blog CRM/partner APIs.
    Returns 403 with a consistent JSON body.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        if request.path.startswith('/api/'):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                try:
                    auth = self.jwt_auth.authenticate(request)
                    if auth:
                        request.user, request.auth = auth
                        user = request.user
                except Exception:
                    pass

            if user and user.is_authenticated and is_blog_user(user):
                if not _path_allowed_for_blog_user(request.path):
                    logger.warning(
                        'Blog user %s blocked from %s %s',
                        user.username,
                        request.method,
                        request.path,
                    )
                    return JsonResponse(
                        {'success': False, 'message': 'Permission denied'},
                        status=403,
                    )

        return self.get_response(request)
