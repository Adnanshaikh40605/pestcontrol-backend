"""Base API views for partner mobile endpoints."""

from rest_framework.views import APIView

from .throttling import PartnerAuthAnonThrottle, PartnerRateThrottle


class PartnerAPIView(APIView):
    """Authenticated partner endpoints — per-partner rate limit."""

    throttle_classes = [PartnerRateThrottle]


class PartnerPublicAPIView(APIView):
    """Register / login / token refresh — IP-based auth throttle only."""

    throttle_classes = [PartnerAuthAnonThrottle]
