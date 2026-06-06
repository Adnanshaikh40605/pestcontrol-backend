from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsCRMOperationalUser
from core.pricing import build_pricing_config_payload, normalize_city_name


class PricingConfigAPIView(APIView):
    """
    GET /api/v1/pricing-config/?city=Lonavala
    Returns city-specific pricing matrix for CRM Create/Edit Booking.
    """

    permission_classes = [IsAuthenticated, IsCRMOperationalUser]

    def get(self, request):
        city = request.query_params.get('city') or request.query_params.get('master_city_name')
        if not city and request.query_params.get('master_city'):
            from core.models import City

            try:
                city_obj = City.objects.get(pk=request.query_params['master_city'])
                city = city_obj.name
            except (City.DoesNotExist, ValueError, TypeError):
                city = None

        payload = build_pricing_config_payload(normalize_city_name(city) or 'Mumbai')
        return Response(payload)
