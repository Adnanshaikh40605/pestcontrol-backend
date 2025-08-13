from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import ClientViewSet, InquiryViewSet, JobCardViewSet, RenewalViewSet
from .auth import CustomTokenObtainPairView

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'inquiries', InquiryViewSet)
router.register(r'jobcards', JobCardViewSet)
router.register(r'renewals', RenewalViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Webhook endpoint for website inquiries
    path('inquiries/webhook/', InquiryViewSet.as_view({'post': 'create'}), name='inquiry-webhook'),
    # JWT Authentication endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]