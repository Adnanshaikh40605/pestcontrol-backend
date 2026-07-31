from rest_framework.views import APIView

from .throttling import CustomerAuthAnonThrottle, CustomerRateThrottle


class CustomerAPIView(APIView):
    throttle_classes = [CustomerRateThrottle]


class CustomerPublicAPIView(APIView):
    throttle_classes = [CustomerAuthAnonThrottle]
