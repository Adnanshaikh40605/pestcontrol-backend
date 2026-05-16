from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from core.auth import CustomTokenObtainPairView
from .api_views import api_docs_view, reference_statistics_view
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from blog.views import SitemapXMLView, RobotsTxtView

def health(request):
    return JsonResponse({
        "status": "ok", 
        "service": "pestcontrol-backend", 
        "version": "1.0.0",
        "endpoint": "main"
    })

def root(request):
    return HttpResponse("PestControl Backend API v1.0.0 - Status: Running", content_type="text/plain")


urlpatterns = [
    path('', root, name='root'),  # Root path for Railway healthcheck
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    
    # Authentication endpoints (CRM Staff)
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # ── CRM Swagger Docs (Admin APIs) ──
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # ── Partner App Swagger Docs (Mobile APIs only) ──
    path(
        'api/partner/schema/',
        SpectacularAPIView.as_view(
            urlconf=None,
            custom_settings={
                'TITLE': 'PestControl Partner App API',
                'DESCRIPTION': (
                    '## Partner App API — For Flutter Mobile App\n\n'
                    'This documentation covers all APIs used by the **Technician Partner Mobile App**.\n\n'
                    '### Authentication\n'
                    'All protected endpoints require a `Bearer` token obtained from `/api/partner/login/`.\n\n'
                    'Add to headers:\n'
                    '```\nAuthorization: Bearer <access_token>\n```\n\n'
                    '### Flow\n'
                    '1. Register → Login → Get Token\n'
                    '2. View Available Bookings → Accept → Start Service → End Service\n'
                    '3. View Profile & Earnings'
                ),
                'VERSION': '1.0.0',
                'SERVERS': [
                    {'url': 'https://pestcontrol-backend-production.up.railway.app', 'description': 'Production'},
                    {'url': 'http://localhost:8000', 'description': 'Local Dev'},
                ],
            }
        ),
        name='partner-schema'
    ),
    path(
        'api/partner/docs/',
        SpectacularSwaggerView.as_view(url_name='partner-schema'),
        name='partner-swagger-ui'
    ),
    
    # Frontend pages
    path('api-docs/', api_docs_view, name='api_docs'),
    path('reference-report/', reference_statistics_view, name='reference_statistics'),
    
    # API endpoints
    path('api/', include('core.urls')),
    path('api/partner/', include('partner.urls')),

    # Blog CMS APIs
    path('api/', include('blog.urls', namespace='blog')),

    # SEO endpoints (served at root level for crawlers)
    path('sitemap.xml', SitemapXMLView.as_view(), name='sitemap'),
    path('robots.txt', RobotsTxtView.as_view(), name='robots'),
]

# Local media only — S3 URLs are served directly from the bucket
if not getattr(settings, 'USE_AWS', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
