"""Public + CRM APIs for partner/customer app version / force-update checks."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .customer_app_version import CustomerAppVersionConfig
from .partner_app_version import PartnerAppVersionConfig
from .permissions import IsSuperAdmin

PARTNER_STORE_URL = (
    'https://play.google.com/store/apps/details?id=com.pestcontrol99.partner'
)
CUSTOMER_STORE_URL = (
    'https://play.google.com/store/apps/details?id=com.pestcontrol99.pest_99_customer_app'
)


def _serialize_config(config, *, app: str) -> dict:
    store_url = PARTNER_STORE_URL if app == 'partner' else CUSTOMER_STORE_URL
    return {
        'app': app,
        'latest_version': config.latest_version,
        'minimum_supported_version': config.minimum_supported_version,
        'force_update': config.force_update,
        'update_title': config.update_title,
        'update_message': config.update_message,
        'store_url': store_url,
        'updated_at': config.updated_at.isoformat() if config.updated_at else None,
    }


def _resolve_app(request) -> str:
    raw = (request.query_params.get('app') or request.data.get('app') or 'partner')
    app = str(raw).strip().lower()
    if app in ('customer', 'customer_app'):
        return 'customer'
    return 'partner'


def _config_for_app(app: str):
    if app == 'customer':
        return CustomerAppVersionConfig.get_solo()
    return PartnerAppVersionConfig.get_solo()


class PartnerAppVersionAPIView(APIView):
    """
    GET /api/app/version/?app=partner|customer

    No authentication required. Checked on every app launch before login.
    Defaults to partner for backward compatibility.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        app = _resolve_app(request)
        config = _config_for_app(app)
        return Response(_serialize_config(config, app=app))


class PartnerAppVersionCRMAPIView(APIView):
    """
    GET/PATCH /api/v1/partner-app-version/?app=partner|customer

    Super admin only — manage force-update policy from CRM/tools.
    """

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        app = _resolve_app(request)
        config = _config_for_app(app)
        return Response(_serialize_config(config, app=app))

    def patch(self, request):
        app = _resolve_app(request)
        config = _config_for_app(app)
        previous_latest = (config.latest_version or '').strip()
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

        new_latest = (config.latest_version or '').strip()
        latest_bumped = bool(new_latest) and new_latest != previous_latest

        # Publishing a new Play Store version: require older installs to update
        # unless the admin explicitly sent force_update/minimum in this request.
        if latest_bumped:
            if 'force_update' not in request.data:
                config.force_update = True
            if 'minimum_supported_version' not in request.data:
                config.minimum_supported_version = new_latest

        # Keep min in sync with latest when enabling force update without an explicit min.
        if (
            config.force_update
            and config.latest_version
            and (
                not config.minimum_supported_version
                or config.minimum_supported_version == '0.0.0'
            )
        ):
            config.minimum_supported_version = config.latest_version
        config.save()
        return Response(_serialize_config(config, app=app))
