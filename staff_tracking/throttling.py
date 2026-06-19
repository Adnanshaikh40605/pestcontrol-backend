"""Rate limits for staff tracking mobile GPS ingest."""

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class TrackingRateThrottle(SimpleRateThrottle):
    """Per tracked staff member — partner JWT uses AnonymousUser."""

    scope = 'staff_tracking'

    def get_cache_key(self, request, view):
        partner = getattr(request, 'partner', None)
        if partner:
            return self.cache_format % {'scope': self.scope, 'ident': f'p{partner.id}'}
        if request.user and request.user.is_authenticated:
            return self.cache_format % {'scope': self.scope, 'ident': f'u{request.user.id}'}
        return None


class TrackingAuthThrottle(AnonRateThrottle):
    scope = 'staff_tracking_auth'
