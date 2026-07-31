"""
Customer App APIs — register/login, catalog, book, track, pay stub, rate.
"""
from __future__ import annotations

import logging

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.models import JobCard, PricingRate, PricingRegion
from core.staff_partner_sync import normalize_mobile

from .models import CustomerAccount
from .permissions import IsCustomer
from .serializers import (
    CatalogRateSerializer,
    CustomerBookSerializer,
    CustomerBookingSerializer,
    CustomerLoginSerializer,
    CustomerPaymentConfirmSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    CustomerRateSerializer,
    CustomerRefreshSerializer,
    CustomerRegisterSerializer,
)
from .services import (
    CustomerAppError,
    confirm_customer_payment,
    create_customer_booking,
    customer_amc_schedule,
    rate_customer_booking,
)
from .utils import CustomerTokenError, generate_customer_tokens, refresh_customer_tokens
from .views_base import CustomerAPIView, CustomerPublicAPIView

logger = logging.getLogger(__name__)


class RegisterAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Auth'], summary='Register customer account')
    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        account = serializer.save()
        tokens = generate_customer_tokens(account)
        return Response(
            {
                'message': 'Registered successfully.',
                'customer': CustomerProfileSerializer(account).data,
                **tokens,
            },
            status=201,
        )


class LoginAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Auth'], summary='Login')
    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        mobile = normalize_mobile(serializer.validated_data['mobile'])
        password = serializer.validated_data['password']
        try:
            account = CustomerAccount.objects.select_related('client').get(mobile=mobile)
        except CustomerAccount.DoesNotExist:
            return Response({'error': 'Invalid mobile or password.', 'code': 'invalid_credentials'}, status=400)
        if not account.check_password(password):
            return Response({'error': 'Invalid mobile or password.', 'code': 'invalid_credentials'}, status=400)
        if not account.is_active:
            return Response({'error': 'Account deactivated.', 'code': 'inactive'}, status=403)
        tokens = generate_customer_tokens(account)
        return Response(
            {
                'message': 'Login successful.',
                'customer': CustomerProfileSerializer(account).data,
                **tokens,
            }
        )


class RefreshTokenAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Auth'], summary='Refresh tokens')
    def post(self, request):
        serializer = CustomerRefreshSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        try:
            tokens = refresh_customer_tokens(serializer.validated_data['refresh'])
        except CustomerTokenError as exc:
            return Response({'error': str(exc), 'code': 'invalid_token'}, status=401)
        return Response(tokens)


class ProfileAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Profile'], summary='Get profile')
    def get(self, request):
        return Response({'customer': CustomerProfileSerializer(request.customer).data})

    @extend_schema(tags=['Customer Profile'], summary='Update profile')
    def put(self, request):
        serializer = CustomerProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        account = request.customer
        data = serializer.validated_data
        if 'full_name' in data:
            account.full_name = data['full_name'].strip()
            account.client.full_name = account.full_name
        if 'email' in data:
            account.email = data['email']
            account.client.email = data['email']
        account.save()
        account.client.save(update_fields=['full_name', 'email', 'updated_at'])
        return Response({'customer': CustomerProfileSerializer(account).data})


class CatalogAPIView(CustomerPublicAPIView):
    """Public catalog — active pricing rates (+ Standard/Premium display)."""

    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Catalog'], summary='List service packages & rates')
    def get(self, request):
        city = (request.query_params.get('city') or '').strip()
        region_slug = (request.query_params.get('region') or '').strip()
        qs = PricingRate.objects.filter(is_active=True).select_related('region')
        if region_slug:
            qs = qs.filter(region__slug__iexact=region_slug)
        elif city:
            qs = qs.filter(
                Q(region__name__icontains=city) | Q(region__city__name__icontains=city)
            )
        else:
            default = PricingRegion.objects.filter(is_default=True, is_active=True).first()
            if default:
                qs = qs.filter(region=default)
        qs = qs.order_by('service_package', 'plan_type', 'area_key')[:200]
        regions = PricingRegion.objects.filter(is_active=True).values('id', 'slug', 'name', 'is_default')
        return Response(
            {
                'regions': list(regions),
                'package_tier_options': [
                    {'value': 'standard', 'label': 'Standard'},
                    {'value': 'premium', 'label': 'Premium'},
                ],
                'results': CatalogRateSerializer(qs, many=True).data,
            }
        )


class BookingListCreateAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='List my bookings')
    def get(self, request):
        status_filter = (request.query_params.get('status') or '').strip()
        qs = JobCard.objects.filter(client=request.customer.client).select_related('client').order_by('-created_at')
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)
        return Response({'results': CustomerBookingSerializer(qs[:100], many=True).data})

    @extend_schema(tags=['Customer Bookings'], summary='Book a service')
    def post(self, request):
        serializer = CustomerBookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        try:
            job = create_customer_booking(request.customer, serializer.validated_data)
        except CustomerAppError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response(
            {
                'message': 'Booking created. Our team will confirm shortly.',
                'booking': CustomerBookingSerializer(job).data,
            },
            status=201,
        )


class BookingDetailAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    def _get_job(self, request, id):
        try:
            return JobCard.objects.select_related('client').get(id=id, client=request.customer.client)
        except JobCard.DoesNotExist:
            return None

    @extend_schema(tags=['Customer Bookings'], summary='Booking detail / track')
    def get(self, request, id):
        job = self._get_job(request, id)
        if not job:
            return Response({'error': 'Booking not found.'}, status=404)
        return Response(CustomerBookingSerializer(job).data)


class ConfirmPaymentAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='Confirm online payment (MVP stub)')
    def post(self, request, id):
        serializer = CustomerPaymentConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        try:
            job = JobCard.objects.get(id=id, client=request.customer.client)
        except JobCard.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)
        try:
            job = confirm_customer_payment(
                request.customer,
                job,
                serializer.validated_data.get('payment_reference') or '',
            )
        except CustomerAppError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response(
            {
                'message': 'Payment recorded.',
                'booking': CustomerBookingSerializer(job).data,
            }
        )


class RateBookingAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='Rate a completed booking')
    def post(self, request, id):
        serializer = CustomerRateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        try:
            job = JobCard.objects.get(id=id, client=request.customer.client)
        except JobCard.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)
        try:
            feedback = rate_customer_booking(request.customer, job, serializer.validated_data)
        except CustomerAppError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response(
            {
                'message': 'Thanks for your feedback!',
                'rating': feedback.rating,
                'remark': feedback.remark,
            }
        )


class ServiceHistoryAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='Completed service history')
    def get(self, request):
        qs = (
            JobCard.objects.filter(client=request.customer.client, status=JobCard.JobStatus.DONE)
            .select_related('client')
            .order_by('-completed_at', '-created_at')[:100]
        )
        return Response({'results': CustomerBookingSerializer(qs, many=True).data})


class AMCScheduleAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='AMC schedule')
    def get(self, request):
        parents = customer_amc_schedule(request.customer)
        results = []
        for parent, children in parents:
            results.append(
                {
                    'parent': CustomerBookingSerializer(parent).data,
                    'visits': CustomerBookingSerializer(children, many=True).data,
                }
            )
        return Response({'results': results})


class InvoiceAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='Simple invoice payload')
    def get(self, request, id):
        try:
            job = JobCard.objects.select_related('client').get(id=id, client=request.customer.client)
        except JobCard.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)
        return Response(
            {
                'booking_id': job.id,
                'code': job.code,
                'client_name': job.client.full_name if job.client else '',
                'mobile': job.client.mobile if job.client else '',
                'service_type': job.service_type,
                'address': job.client_address,
                'amount': str(job.total_amount or job.price or '0'),
                'payment_status': job.payment_status,
                'payment_mode': job.payment_mode,
                'package_tier': job.package_tier,
                'schedule_datetime': job.schedule_datetime,
                'status': job.status,
                'issued_at': job.completed_at or job.created_at,
            }
        )
