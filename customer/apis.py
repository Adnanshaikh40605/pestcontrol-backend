"""
Customer App APIs — register/login, OTP auth, catalog, book, track, pay stub, rate.
"""
from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.models import City, JobCard, Location, PricingRate, PricingRegion
from core.staff_partner_sync import normalize_mobile

from .account_deletion import CustomerAccountDeletionError, permanently_delete_customer_account
from .models import CustomerAccount, CustomerOTPChallenge
from .permissions import IsCustomer
from .serializers import (
    CatalogRateSerializer,
    CustomerBookSerializer,
    CustomerBookingSerializer,
    CustomerCancelSerializer,
    CustomerCitySerializer,
    CustomerComplaintSerializer,
    CustomerDeleteAccountSerializer,
    CustomerLoginSerializer,
    CustomerLocationSerializer,
    CustomerOTPSendSerializer,
    CustomerOTPVerifySerializer,
    CustomerPaymentConfirmSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    CustomerRateSerializer,
    CustomerRefreshSerializer,
    CustomerRegisterSerializer,
)
from .services import (
    CustomerAppError,
    cancel_customer_booking,
    confirm_customer_payment,
    create_customer_booking,
    create_customer_complaint,
    customer_amc_schedule,
    rate_customer_booking,
)
from .utils import CustomerTokenError, generate_customer_tokens, refresh_customer_tokens
from .places import PlacesProxyError, places_autocomplete, places_details, places_reverse_geocode
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

    @extend_schema(tags=['Customer Auth'], summary='Login (password — legacy)')
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


def _reviewer_mobiles() -> set[str]:
    raw = getattr(settings, 'CUSTOMER_OTP_REVIEWER_MOBILES', '') or ''
    return {m.strip() for m in raw.split(',') if m.strip()}


def _generate_customer_otp(mobile: str = '') -> str:
    # Play Console reviewer mobiles get a stable OTP (not global for all users).
    if mobile and mobile in _reviewer_mobiles():
        code = getattr(settings, 'CUSTOMER_OTP_REVIEWER_CODE', None) or '2468'
        return str(code).zfill(4)[:4]
    fixed = getattr(settings, 'CUSTOMER_OTP_FIXED', None)
    if fixed:
        return str(fixed).zfill(4)[:4]
    if settings.DEBUG:
        return '1234'
    return f'{secrets.randbelow(10000):04d}'


class SendOTPAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Auth'], summary='Send 4-digit OTP (login / register)')
    def post(self, request):
        serializer = CustomerOTPSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        mobile = serializer.validated_data['mobile']
        purpose = serializer.validated_data['purpose']
        full_name = serializer.validated_data.get('full_name') or ''

        exists = CustomerAccount.objects.filter(mobile=mobile).exists()
        # Allow login OTP even when no account exists — verify step returns
        # not_registered with a clear register CTA (better UX than blocking send).
        if purpose == CustomerOTPChallenge.PURPOSE_REGISTER and exists:
            return Response(
                {'error': 'An account with this mobile already exists. Please login.', 'code': 'already_registered'},
                status=400,
            )

        otp = _generate_customer_otp(mobile)
        is_reviewer = mobile in _reviewer_mobiles()
        ttl = int(getattr(settings, 'CUSTOMER_OTP_TTL_SECONDS', 300))
        # Reviewer OTP stays valid longer for Play Console testing.
        if is_reviewer:
            ttl = max(ttl, 7 * 24 * 3600)
        challenge = CustomerOTPChallenge(
            mobile=mobile,
            purpose=purpose,
            full_name=full_name,
            expires_at=timezone.now() + timedelta(seconds=ttl),
        )
        challenge.set_otp(otp)
        challenge.save()

        # Never log plaintext OTP in production (except reviewer mobiles — ops need it).
        if settings.DEBUG or is_reviewer:
            logger.info('Customer OTP generated mobile=%s purpose=%s otp=%s reviewer=%s', mobile, purpose, otp, is_reviewer)
        else:
            logger.info('Customer OTP generated mobile=%s purpose=%s', mobile, purpose)

        delivery = 'queued'
        if is_reviewer:
            delivery = 'reviewer_fixed'
        elif not settings.DEBUG:
            try:
                from core.whatsflow_pc99 import notify_customer_otp

                sent = notify_customer_otp(
                    mobile=mobile,
                    otp=otp,
                    purpose=purpose,
                    customer_name=full_name or None,
                )
                delivery = 'whatsapp' if sent else 'pending_channel'
                if not sent:
                    logger.error(
                        'Customer OTP could not be delivered via WhatsApp mobile=%s — '
                        'set CUSTOMER_OTP_WHATSAPP_TEMPLATE and WHATSFLOW_API_KEY',
                        mobile,
                    )
            except Exception:
                logger.exception('Customer OTP WhatsApp delivery failed mobile=%s', mobile)
                delivery = 'pending_channel'

        payload = {
            'message': 'OTP sent successfully.' if delivery != 'pending_channel' else (
                'OTP generated. Delivery channel is not configured; contact support if you did not receive it.'
            ),
            'mobile': mobile,
            'purpose': purpose,
            'expires_in': ttl,
            'delivery': delivery,
        }
        # Expose OTP only in local DEBUG builds — never in production responses.
        if settings.DEBUG:
            payload['dev_otp'] = otp
        return Response(payload)


class VerifyOTPAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Auth'], summary='Verify 4-digit OTP and issue tokens')
    def post(self, request):
        serializer = CustomerOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        mobile = serializer.validated_data['mobile']
        otp = serializer.validated_data['otp']
        purpose = serializer.validated_data['purpose']
        full_name = serializer.validated_data.get('full_name') or ''

        challenge = (
            CustomerOTPChallenge.objects.filter(mobile=mobile, purpose=purpose, consumed_at__isnull=True)
            .order_by('-created_at')
            .first()
        )
        if not challenge:
            return Response({'error': 'OTP expired or not found. Please request a new OTP.', 'code': 'otp_missing'}, status=400)
        if challenge.is_expired:
            return Response({'error': 'OTP expired. Please request a new OTP.', 'code': 'otp_expired'}, status=400)
        if challenge.attempts >= 5:
            return Response({'error': 'Too many incorrect attempts. Request a new OTP.', 'code': 'otp_locked'}, status=400)

        if not challenge.check_otp(otp):
            challenge.attempts += 1
            challenge.save(update_fields=['attempts'])
            return Response({'error': 'Invalid OTP. Please try again.', 'code': 'otp_invalid'}, status=400)

        challenge.consumed_at = timezone.now()
        challenge.save(update_fields=['consumed_at'])

        if purpose == CustomerOTPChallenge.PURPOSE_REGISTER:
            name = full_name or challenge.full_name
            if len(name.strip()) < 2:
                return Response({'error': 'Name is required to create an account.', 'code': 'name_required'}, status=400)
            reg = CustomerRegisterSerializer(
                data={'full_name': name.strip(), 'mobile': mobile, 'password': ''}
            )
            if not reg.is_valid():
                return Response({'errors': reg.errors}, status=400)
            account = reg.save()
            message = 'Registered successfully.'
        else:
            try:
                account = CustomerAccount.objects.select_related('client').get(mobile=mobile)
            except CustomerAccount.DoesNotExist:
                return Response(
                    {
                        'error': (
                            'No account found with this mobile number. '
                            'Please register to continue.'
                        ),
                        'code': 'not_registered',
                        'mobile': mobile,
                        'action': 'register',
                    },
                    status=404,
                )
            if not account.is_active:
                return Response({'error': 'Account deactivated.', 'code': 'inactive'}, status=403)
            message = 'Login successful.'

        tokens = generate_customer_tokens(account)
        return Response(
            {
                'message': message,
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


class DeleteAccountAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Profile'], summary='Permanently delete my customer account')
    def post(self, request):
        serializer = CustomerDeleteAccountSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        try:
            permanently_delete_customer_account(request.customer)
        except CustomerAccountDeletionError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response({'message': 'Account deleted successfully.'})


class ComplaintCreateAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Support'], summary='Submit complaint / re-service request')
    def post(self, request):
        serializer = CustomerComplaintSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        try:
            job = create_customer_complaint(request.customer, serializer.validated_data)
        except CustomerAppError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response(
            {
                'message': 'Complaint submitted. Our team will contact you shortly.',
                'booking': CustomerBookingSerializer(job).data,
            },
            status=201,
        )


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


class CitiesAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Master Data'], summary='List active CRM cities')
    def get(self, request):
        qs = City.objects.filter(is_active=True).select_related('state').order_by('name')
        return Response({
            'results': CustomerCitySerializer(qs, many=True).data,
        })


class LocationsAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Master Data'], summary='List active CRM areas for a city')
    def get(self, request):
        city_id = request.query_params.get('city_id') or request.query_params.get('city')
        if not city_id:
            return Response(
                {'error': 'city_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            city_pk = int(city_id)
        except (TypeError, ValueError):
            return Response({'error': 'city_id must be an integer.'}, status=400)
        if not City.objects.filter(id=city_pk, is_active=True).exists():
            return Response({'error': 'City not found.'}, status=404)
        qs = Location.objects.filter(city_id=city_pk, is_active=True).order_by('name')
        return Response({
            'results': CustomerLocationSerializer(qs, many=True).data,
        })


class PlacesAutocompleteAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Places'], summary='Google Places autocomplete (server proxy)')
    def get(self, request):
        try:
            results = places_autocomplete(request.query_params.get('input') or '')
        except PlacesProxyError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=exc.status)
        return Response({'results': results})


class PlacesDetailsAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Places'], summary='Google Place details (server proxy)')
    def get(self, request):
        try:
            data = places_details(request.query_params.get('place_id') or '')
        except PlacesProxyError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=exc.status)
        return Response(data)


class PlacesReverseGeocodeAPIView(CustomerPublicAPIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=['Customer Places'], summary='Reverse geocode lat/lng (server proxy)')
    def get(self, request):
        try:
            latitude = float(request.query_params.get('latitude') or request.query_params.get('lat') or '')
            longitude = float(request.query_params.get('longitude') or request.query_params.get('lng') or '')
        except (TypeError, ValueError):
            return Response({'error': 'latitude and longitude are required.'}, status=400)
        try:
            data = places_reverse_geocode(latitude, longitude)
        except PlacesProxyError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=exc.status)
        return Response(data)


class BookingListCreateAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='List my bookings')
    def get(self, request):
        status_filter = (request.query_params.get('status') or '').strip()
        qs = JobCard.objects.filter(client=request.customer.client).select_related(
            'client', 'technician', 'partner', 'partner__core_technician',
        ).order_by('-created_at')
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)
        return Response({
            'results': CustomerBookingSerializer(qs[:100], many=True, context={'request': request}).data,
        })

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
                'booking': CustomerBookingSerializer(job, context={'request': request}).data,
            },
            status=201,
        )


class BookingDetailAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    def _get_job(self, request, id):
        try:
            return JobCard.objects.select_related(
                'client', 'technician', 'partner', 'partner__core_technician',
            ).get(id=id, client=request.customer.client)
        except JobCard.DoesNotExist:
            return None

    @extend_schema(tags=['Customer Bookings'], summary='Booking detail / track')
    def get(self, request, id):
        job = self._get_job(request, id)
        if not job:
            return Response({'error': 'Booking not found.'}, status=404)
        return Response(CustomerBookingSerializer(job, context={'request': request}).data)


class CancelBookingAPIView(CustomerAPIView):
    permission_classes = [IsCustomer]

    @extend_schema(tags=['Customer Bookings'], summary='Cancel a booking with reason')
    def post(self, request, id):
        serializer = CustomerCancelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        try:
            job = JobCard.objects.select_related(
                'client', 'technician', 'partner', 'partner__core_technician',
            ).get(id=id, client=request.customer.client)
        except JobCard.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=404)
        try:
            job = cancel_customer_booking(
                request.customer,
                job,
                reason=serializer.validated_data['reason'],
            )
        except CustomerAppError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response({
            'message': 'Booking cancelled.',
            'booking': CustomerBookingSerializer(job, context={'request': request}).data,
        })


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
                'code': job.code or str(job.id),
                'client_name': job.client.full_name if job.client else '',
                'mobile': job.client.mobile if job.client else '',
                'service_type': job.service_type,
                'address': job.client_address or (job.client.address if job.client else '') or '',
                'city': job.city or (job.client.city if job.client else '') or '',
                'area': getattr(job, 'area', None) or '',
                'property_type': job.property_type or '',
                'bhk_size': job.bhk_size or '',
                'amount': str(job.total_amount or job.price or '0'),
                'payment_status': job.payment_status,
                'payment_mode': job.payment_mode,
                'package_tier': job.package_tier,
                'booking_type': job.booking_type,
                'schedule_datetime': job.schedule_datetime,
                'time_slot': job.time_slot or '',
                'status': job.status,
                'issued_at': job.completed_at or job.created_at,
            }
        )
