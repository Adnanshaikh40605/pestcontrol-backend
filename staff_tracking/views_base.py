from rest_framework.views import APIView

from .throttling import TrackingAuthThrottle, TrackingRateThrottle


class TrackingAPIView(APIView):
    """Authenticated tracking endpoints — per-staff rate limit."""
    throttle_classes = [TrackingRateThrottle]


class TrackingPublicAPIView(APIView):
    """Login / refresh — IP throttle."""
    throttle_classes = [TrackingAuthThrottle]
