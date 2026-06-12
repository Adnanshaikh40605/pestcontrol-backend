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
        master_city_id = None
        if request.query_params.get('master_city'):
            from core.models import City

            try:
                master_city_id = int(request.query_params['master_city'])
                if not city:
                    city_obj = City.objects.get(pk=master_city_id)
                    city = city_obj.name
            except (City.DoesNotExist, ValueError, TypeError):
                master_city_id = None

        payload = build_pricing_config_payload(
            normalize_city_name(city) or None,
            master_city_id=master_city_id,
        )
        response = Response(payload)
        response['Cache-Control'] = 'no-store'
        return response
