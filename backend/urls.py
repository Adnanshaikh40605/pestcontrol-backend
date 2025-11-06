"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
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
    
    # Authentication endpoints
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Swagger UI Documentation (schema endpoint is internal, not exposed)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Frontend pages
    path('api-docs/', api_docs_view, name='api_docs'),
    path('reference-report/', reference_statistics_view, name='reference_statistics'),
    
    # API endpoints
    path('api/', include('core.urls')),
]
