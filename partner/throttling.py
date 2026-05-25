"""Rate limits for partner mobile API (per partner, not shared anonymous bucket)."""

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class PartnerRateThrottle(SimpleRateThrottle):
    """
    Partner JWT auth sets request.user to AnonymousUser, so default DRF throttles
    incorrectly apply the global ``anon`` limit (100/hour) to every technician.

    This throttle keys by ``request.partner.id`` instead.
    """

    scope = 'partner'

    def get_cache_key(self, request, view):
        partner = getattr(request, 'partner', None)
        if not partner:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': partner.id,
        }


class PartnerAuthAnonThrottle(AnonRateThrottle):
    """Login / register / refresh — per IP, separate from partner mobile traffic."""

    scope = 'partner_auth'
