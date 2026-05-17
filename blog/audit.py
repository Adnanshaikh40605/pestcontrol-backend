"""Blog CMS audit logging."""

import logging

from .models import BlogAuditLog

logger = logging.getLogger(__name__)


def _client_ip(request):
    if not request:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_blog_audit(user, action: str, blog=None, details: str = '', request=None):
    """Persist a blog audit event."""
    try:
        BlogAuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            blog=blog,
            details=details or '',
            ip_address=_client_ip(request),
            user_agent=(request.META.get('HTTP_USER_AGENT', '')[:512] if request else ''),
        )
    except Exception as exc:
        logger.warning('Failed to write blog audit log: %s', exc)
