"""Public + CRM APIs for partner app version / force-update checks."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .partner_app_version import PartnerAppVersionConfig
from .permissions import IsSuperAdmin


def _serialize_config(config: PartnerAppVersionConfig) -> dict:
    return {
        'latest_version': config.latest_version,
        'minimum_supported_version': config.minimum_supported_version,
        'force_update': config.force_update,
        'update_title': config.update_title,
        'update_message': config.update_message,
        'updated_at': config.updated_at.isoformat() if config.updated_at else None,
    }


class PartnerAppVersionAPIView(APIView):
    """
    GET /api/app/version/

    No authentication required. Used on every partner app launch before login.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        config = PartnerAppVersionConfig.get_solo()
        return Response(_serialize_config(config))


class PartnerAppVersionCRMAPIView(APIView):
    """
    GET/PATCH /api/v1/partner-app-version/

    Super admin only — manage force-update policy from CRM.
    """

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        config = PartnerAppVersionConfig.get_solo()
        return Response(_serialize_config(config))

    def patch(self, request):
        config = PartnerAppVersionConfig.get_solo()
        allowed = {
            'latest_version',
            'minimum_supported_version',
            'force_update',
            'update_title',
            'update_message',
        }
        for key, value in request.data.items():
            if key not in allowed:
                continue
            setattr(config, key, value)
        config.save()
        return Response(_serialize_config(config))
