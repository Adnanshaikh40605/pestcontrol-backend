"""
Partner App APIs — Complete implementation for Flutter mobile app.

All endpoints are grouped as:
  - Authentication (Register, Login, Refresh Token, FCM Update)
  - Bookings (Available, Accepted, Completed, Detail, Accept, Reject, Start, Complete)
  - Profile (My Profile, Update Profile, Stats, Earnings, Ratings)
"""

import logging
from django.utils import timezone
from django.db.models import Avg, Sum, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Partner, PartnerEarning, PartnerRating
from .serializers import (
    PartnerSerializer,
    PartnerRegisterSerializer,
    PartnerLoginSerializer,
    PartnerRefreshSerializer,
    PartnerUpdateSerializer,
    PartnerFCMSerializer,
    PartnerBookingListSerializer,
    PartnerBookingDetailSerializer,
    PartnerCompleteBookingSerializer,
    PartnerEarningSerializer,
    PartnerProfileStatsSerializer,
)
from .permissions import IsPartner, IsPartnerAdmin, IsPartnerAuthenticated
from .utils import PartnerTokenError, generate_partner_tokens, refresh_partner_tokens
from .services import (
    PartnerBookingError,
    broadcast_pending_filter,
    partner_accept_booking,
    partner_start_service,
    partner_complete_booking,
)
from core.models import JobCard
from core.services import JobCardService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────

class RegisterAPIView(APIView):
    """
    POST /api/partner/register/
    Register a new Partner (Technician) account.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Register a new partner account",
        description=(
            "Create a new technician / technician_admin account. "
            "After registration, use /login/ to get tokens."
        ),
        request=PartnerRegisterSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "partner": {"type": "object"},
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                }
            }
        },
        examples=[
            OpenApiExample(
                "Technician Registration",
                value={
                    "full_name": "Arshad Khan",
                    "mobile": "9876543210",
                    "password": "secure123",
                    "role": "technician"
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = PartnerRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        partner = serializer.save()
        tokens = generate_partner_tokens(partner)

        return Response(
            {
                "message": "Registration successful. Welcome aboard!",
                "partner": PartnerSerializer(partner).data,
                **tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    """
    POST /api/partner/login/
    Login with mobile number and password.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Partner login",
        description="Login using mobile number and password. Returns JWT access & refresh tokens.",
        request=PartnerLoginSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "partner": {"type": "object"},
                }
            }
        },
        examples=[
            OpenApiExample(
                "Login Example",
                value={"mobile": "9876543210", "password": "secure123"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = PartnerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        from core.staff_partner_sync import normalize_mobile

        mobile = normalize_mobile(serializer.validated_data['mobile'])
        password = serializer.validated_data['password']

        try:
            partner = Partner.objects.get(mobile=mobile)
        except Partner.DoesNotExist:
            return Response(
                {"error": "No account found with this mobile number."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not partner.is_active:
            return Response(
                {"error": "Your account has been deactivated. Contact admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not partner.check_password(password):
            return Response(
                {"error": "Incorrect password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = generate_partner_tokens(partner)
        logger.info(f"Partner login: {partner.full_name} ({partner.mobile})")

        return Response(
            {
                **tokens,
                "partner": PartnerSerializer(partner).data,
                "is_app_approved": partner.is_app_approved,
            },
            status=status.HTTP_200_OK,
        )


class RefreshTokenAPIView(APIView):
    """
    POST /api/partner/token/refresh/
    Rotate partner refresh token and return new access + refresh pair.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Refresh partner JWT tokens",
        description=(
            "Exchange a valid refresh token for a new access + refresh pair. "
            "Old refresh token is revoked (rotation). "
            "Fails if partner is deactivated or refresh is expired (>60 days)."
        ),
        request=PartnerRefreshSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                },
            }
        },
    )
    def post(self, request):
        serializer = PartnerRefreshSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tokens = refresh_partner_tokens(serializer.validated_data['refresh'])
        except PartnerTokenError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(tokens, status=status.HTTP_200_OK)


class SaveFCMTokenAPIView(APIView):
    """
    POST /api/partner/save-fcm-token/
    Register or update device FCM token (deduplicated).
    """
    permission_classes = [IsPartnerAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Save FCM device token",
        request=PartnerFCMSerializer,
    )
    def post(self, request):
        serializer = PartnerFCMSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        from partner.notification_service import register_device_token

        try:
            register_device_token(
                request.partner,
                serializer.validated_data['fcm_token'],
                serializer.validated_data.get('device_type', 'android'),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "FCM token saved successfully."})


class RemoveFCMTokenAPIView(APIView):
    """POST /api/partner/remove-fcm-token/ — on logout."""
    permission_classes = [IsPartnerAuthenticated]

    @extend_schema(tags=["Notifications"], summary="Remove FCM token on logout")
    def post(self, request):
        from partner.notification_service import deactivate_device_token

        token = request.data.get('fcm_token')
        count = deactivate_device_token(request.partner, token)
        return Response({"message": "FCM token removed.", "deactivated": count})


# Legacy alias
UpdateFCMTokenAPIView = SaveFCMTokenAPIView


class PartnerNotificationsAPIView(APIView):
    """GET /api/partner/notifications/ — in-app notification history."""
    permission_classes = [IsPartner]

    @extend_schema(tags=["Notifications"], summary="List partner notifications")
    def get(self, request):
        from partner.models import PartnerNotification
        from partner.serializers import PartnerNotificationSerializer

        base_qs = PartnerNotification.objects.filter(partner=request.partner)
        unread = base_qs.filter(is_read=False).count()
        qs = base_qs.select_related('booking').order_by('-created_at')[:100]
        return Response({
            "unread_count": unread,
            "results": PartnerNotificationSerializer(qs, many=True).data,
        })


class MarkNotificationReadAPIView(APIView):
    """POST /api/partner/notifications/<id>/read/"""
    permission_classes = [IsPartner]

    def post(self, request, id):
        from partner.models import PartnerNotification

        updated = PartnerNotification.objects.filter(
            partner=request.partner, pk=id, is_read=False
        ).update(is_read=True)
        if not updated:
            return Response({"error": "Not found."}, status=404)
        return Response({"message": "Marked as read."})


class PushHealthAPIView(APIView):
    """GET /api/partner/push-health/ — verify FCM config (authenticated partner)."""
    permission_classes = [IsPartnerAuthenticated]

    def get(self, request):
        from partner.notification_service import active_tokens_for_partners
        from partner.push_service import is_fcm_configured

        partner = request.partner
        my_tokens = list(
            partner.device_tokens.filter(is_active=True).values_list('fcm_token', flat=True)
        )
        return Response({
            'fcm_configured': is_fcm_configured(),
            'partner_id': partner.id,
            'is_app_approved': partner.is_app_approved,
            'device_tokens_count': len(my_tokens),
            'has_legacy_fcm_token': bool(partner.fcm_token),
            'pool_active_tokens': len(active_tokens_for_partners()),
        })


class MarkAllNotificationsReadAPIView(APIView):
    """POST /api/partner/notifications/mark-all-read/"""
    permission_classes = [IsPartner]

    def post(self, request):
        from partner.models import PartnerNotification

        count = PartnerNotification.objects.filter(
            partner=request.partner, is_read=False
        ).update(is_read=True)
        return Response({"message": "All marked read.", "count": count})


# ─────────────────────────────────────────────────────────────────────────────
# BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

class AvailableBookingsAPIView(APIView):
    """
    GET /api/partner/bookings/available/
    Returns all bookings assigned to this partner that are PENDING (not yet accepted).
    Also returns the count for the tab badge.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Get available (pending) bookings",
        description=(
            "Returns bookings assigned to the logged-in partner with partner_status='pending'. "
            "These appear in the **Bookings** tab on the app."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "results": {"type": "array"},
                }
            }
        },
    )
    def get(self, request):
        partner = request.partner
        jobs = JobCard.objects.filter(
            broadcast_pending_filter()
            | Q(partner=partner, partner_status=JobCard.PartnerStatus.PENDING)
        ).select_related('client', 'master_city', 'master_location').order_by('schedule_datetime')

        serializer = PartnerBookingListSerializer(jobs, many=True, context={'request': request})
        return Response({"count": jobs.count(), "results": serializer.data})


class AcceptedBookingsAPIView(APIView):
    """
    GET /api/partner/bookings/accepted/
    Returns all accepted bookings (not yet completed) for this partner.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Get accepted bookings",
        description=(
            "Returns bookings the partner has accepted (partner_status='accepted' or 'in_service'). "
            "These appear in the **Accepted** tab on the app."
        ),
    )
    def get(self, request):
        partner = request.partner
        jobs = JobCard.objects.filter(
            partner=partner,
            partner_status__in=[
                JobCard.PartnerStatus.ACCEPTED,
                JobCard.PartnerStatus.IN_SERVICE,
            ],
        ).select_related('client', 'master_city', 'master_location').order_by('schedule_datetime')

        serializer = PartnerBookingListSerializer(jobs, many=True, context={'request': request})
        return Response({"count": jobs.count(), "results": serializer.data})


class CompletedBookingsAPIView(APIView):
    """
    GET /api/partner/bookings/completed/
    Returns all completed bookings for this partner.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Get completed bookings",
        description="Returns bookings the partner has marked as done. Shown in **Completed** tab.",
    )
    def get(self, request):
        partner = request.partner
        jobs = JobCard.objects.filter(
            partner=partner,
            partner_status=JobCard.PartnerStatus.COMPLETED,
        ).select_related('client', 'master_city', 'master_location').order_by('-completed_at')

        serializer = PartnerBookingListSerializer(jobs, many=True, context={'request': request})
        return Response({"count": jobs.count(), "results": serializer.data})


class BookingDetailAPIView(APIView):
    """
    GET /api/partner/bookings/{id}/
    Returns full details of a specific booking.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Get booking details",
        description="Returns full booking details including customer info, property, service, payment, and schedule.",
    )
    def get(self, request, id):
        partner = request.partner
        try:
            job = JobCard.objects.select_related(
                'client', 'master_city', 'master_location', 'master_state', 'technician'
            ).get(id=id, partner=partner)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found or not assigned to you."}, status=404)

        serializer = PartnerBookingDetailSerializer(job, context={'request': request})
        return Response(serializer.data)


class BookingCountsAPIView(APIView):
    """
    GET /api/partner/bookings/counts/
    Returns tab badge counts for Available, Accepted, Completed.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Get booking tab counts",
        description="Returns counts for Available, Accepted, and Completed tabs for badge display.",
    )
    def get(self, request):
        partner = request.partner
        pool = JobCard.objects.filter(broadcast_pending_filter()).count()
        mine = JobCard.objects.filter(partner=partner, partner_status='pending').count()
        available = pool + mine
        accepted = JobCard.objects.filter(
            partner=partner, partner_status__in=['accepted', 'in_service']
        ).count()
        completed = JobCard.objects.filter(partner=partner, partner_status='completed').count()

        return Response({
            "available": available,
            "accepted": accepted,
            "completed": completed,
        })


class AcceptBookingAPIView(APIView):
    """
    POST /api/partner/bookings/{id}/accept/
    Accept a pending booking.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Accept a booking",
        description=(
            "Accepts a pending booking. Changes partner_status from 'pending' to 'accepted'. "
            "Changes job status to 'On Process'."
        ),
        request=None,
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    )
    def post(self, request, id):
        partner = request.partner
        try:
            job = JobCard.objects.get(id=id)
            job = partner_accept_booking(job, partner)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found."}, status=404)
        except PartnerBookingError as exc:
            return Response({"error": exc.message, "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Partner {partner.full_name} accepted booking #{job.id}")
        return Response({
            "message": "Booking accepted! Check the Accepted tab.",
            "status": job.status,
            "partner_status": job.partner_status,
        })


class RejectBookingAPIView(APIView):
    """
    POST /api/partner/bookings/{id}/reject/
    Reject a pending booking.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Reject a booking",
        description="Reject a pending booking. The booking goes back to the CRM for reassignment.",
        request={
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Optional rejection reason"}
            }
        },
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    )
    def post(self, request, id):
        partner = request.partner
        try:
            job = JobCard.objects.get(
                Q(id=id)
                & (
                    Q(partner=partner)
                    | Q(partner__isnull=True, sent_to_app_at__isnull=False)
                )
            )
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found."}, status=404)

        if job.partner_status != JobCard.PartnerStatus.PENDING:
            return Response(
                {"error": f"Cannot reject a booking with status '{job.partner_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get('reason', '')
        job.partner_status = JobCard.PartnerStatus.REJECTED
        job.partner = None
        job.sent_to_app_at = None
        job.technician = None
        job.assigned_to = ''
        job.sync_booking_category()
        job.status = job.status_after_technician_removal()
        job.removal_remarks = f"Rejected by partner {partner.full_name}: {reason}"
        job.save(
            update_fields=[
                'partner_status', 'partner', 'sent_to_app_at', 'technician',
                'assigned_to', 'status', 'removal_remarks', 'booking_category',
            ]
        )

        logger.info(f"Partner {partner.full_name} rejected booking #{job.id}. Reason: {reason}")
        return Response({"message": "Booking rejected. Admin will reassign it."})


class StartServiceAPIView(APIView):
    """
    POST /api/partner/bookings/{id}/start/
    Mark service as started (multipart: selfie image required).
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Start service with selfie",
        description=(
            "Upload a selfie image (field name `selfie`) to start the job. "
            "Sets partner_status to 'in_service' and records start time."
        ),
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'selfie': {'type': 'string', 'format': 'binary'},
                },
                'required': ['selfie'],
            }
        },
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    )
    def post(self, request, id):
        partner = request.partner
        selfie = request.FILES.get('selfie')
        try:
            job = JobCard.objects.get(id=id, partner=partner)
            job = partner_start_service(job, partner, selfie)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found or not assigned to you."}, status=404)
        except PartnerBookingError as exc:
            return Response({"error": exc.message, "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Partner {partner.full_name} started service for booking #{job.id}")
        return Response({
            "message": "Service started! Use End Service when finished.",
            "partner_status": job.partner_status,
            "started_at": job.started_at,
        })


class CompleteBookingAPIView(APIView):
    """
    POST /api/partner/bookings/{id}/complete/
    End service and mark booking as completed.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Complete a booking (End Service)",
        description=(
            "Mark the service as completed. Requires payment_mode. "
            "Sets job status to 'Done', partner_status to 'completed'. "
            "Triggers AMC follow-up automation if applicable."
        ),
        request=PartnerCompleteBookingSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "next_service_date": {"type": "string"},
                }
            }
        },
        examples=[
            OpenApiExample("Pay by Cash", value={"payment_mode": "Cash"}, request_only=True),
            OpenApiExample("Pay Online", value={"payment_mode": "Online"}, request_only=True),
        ],
    )
    def post(self, request, id):
        partner = request.partner
        serializer = PartnerCompleteBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        payment_mode = serializer.validated_data['payment_mode']
        try:
            job = JobCard.objects.get(id=id, partner=partner)
            job = partner_complete_booking(job, partner, payment_mode)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found or not assigned to you."}, status=404)
        except PartnerBookingError as exc:
            return Response({"error": exc.message, "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)

        next_service_date = None
        try:
            result = JobCardService.handle_job_completion(job)
            if result and hasattr(result, 'next_service_date'):
                next_service_date = str(result.next_service_date)
        except Exception as e:
            logger.error(f"Failed to trigger follow-up automation for booking #{job.id}: {e}")

        logger.info(
            f"Partner {partner.full_name} completed booking #{job.id} via {payment_mode}"
        )

        return Response({
            "message": f"Service completed! Payment recorded as {payment_mode}.",
            "status": job.status,
            "partner_status": job.partner_status,
            "payment_mode": job.payment_mode,
            "payment_status": job.payment_status,
            "next_service_date": next_service_date,
        })


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────

class ProfileAPIView(APIView):
    """
    GET  /api/partner/profile/       → My profile + stats
    PUT  /api/partner/profile/       → Update profile
    """
    permission_classes = [IsPartnerAuthenticated]

    @extend_schema(
        tags=["Profile"],
        summary="Get my profile with statistics",
        description=(
            "Returns partner profile along with: total jobs, completed jobs, "
            "accepted jobs, service calls, average rating, and total earnings."
        ),
    )
    def get(self, request):
        partner = request.partner

        # Stats
        total_jobs = JobCard.objects.filter(partner=partner).count()
        completed_jobs = JobCard.objects.filter(
            partner=partner, partner_status=JobCard.PartnerStatus.COMPLETED
        ).count()
        accepted_jobs = JobCard.objects.filter(
            partner=partner,
            partner_status__in=[JobCard.PartnerStatus.ACCEPTED, JobCard.PartnerStatus.IN_SERVICE]
        ).count()
        available_jobs = JobCard.objects.filter(
            partner=partner, partner_status=JobCard.PartnerStatus.PENDING
        ).count()
        service_calls = JobCard.objects.filter(
            partner=partner,
            booking_type__in=[JobCard.BookingType.AMC_FOLLOWUP, JobCard.BookingType.SERVICE_CALL],
        ).count()

        avg_rating_result = PartnerRating.objects.filter(partner=partner).aggregate(Avg('rating'))
        avg_rating = round(avg_rating_result['rating__avg'] or 0, 1)

        total_earnings_result = PartnerEarning.objects.filter(partner=partner).aggregate(Sum('amount'))
        total_earnings = total_earnings_result['amount__sum'] or 0

        pool_available = JobCard.objects.filter(broadcast_pending_filter()).count()

        ctx = {"request": request}
        return Response({
            "partner": PartnerSerializer(partner, context=ctx).data,
            "is_app_approved": partner.is_app_approved,
            "stats": {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "accepted_jobs": accepted_jobs,
                "available_jobs": available_jobs + (pool_available if partner.is_app_approved else 0),
                "service_calls": service_calls,
                "avg_rating": avg_rating,
                "total_earnings": str(total_earnings),
            },
        })

    @extend_schema(
        tags=["Profile"],
        summary="Update my profile",
        description="Update full_name, profile_image, or bank details.",
        request=PartnerUpdateSerializer,
    )
    def put(self, request):
        partner = request.partner
        serializer = PartnerUpdateSerializer(partner, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        ctx = {"request": request}
        return Response({
            "message": "Profile updated successfully.",
            "partner": PartnerSerializer(request.partner, context=ctx).data,
        })


class EarningsHistoryAPIView(APIView):
    """
    GET /api/partner/earnings/
    Returns earnings history for the logged-in partner.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Profile"],
        summary="Get earnings history",
        description="Returns a list of all earnings entries for the partner.",
    )
    def get(self, request):
        partner = request.partner
        earnings = PartnerEarning.objects.filter(partner=partner).select_related('job').order_by('-created_at')
        serializer = PartnerEarningSerializer(earnings, many=True)

        total = earnings.aggregate(Sum('amount'))['amount__sum'] or 0

        return Response({
            "total_earnings": str(total),
            "results": serializer.data,
        })


class RatingsAPIView(APIView):
    """
    GET /api/partner/ratings/
    Returns ratings given to the logged-in partner.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Profile"],
        summary="Get my ratings",
        description="Returns all ratings and feedback given to this partner by customers.",
    )
    def get(self, request):
        partner = request.partner
        ratings = PartnerRating.objects.filter(partner=partner).select_related('job').order_by('-created_at')
        avg = ratings.aggregate(Avg('rating'))['rating__avg'] or 0

        data = []
        for r in ratings:
            data.append({
                "job_id": r.job_id,
                "job_code": r.job.code if r.job else "",
                "service_type": r.job.service_type if r.job else "",
                "rating": r.rating,
                "feedback": r.feedback,
                "date": r.created_at,
            })

        return Response({
            "avg_rating": round(avg, 1),
            "total_ratings": ratings.count(),
            "results": data,
        })


class ReferClientAPIView(APIView):
    """
    POST /api/partner/refer-client/
    Submit a client referral from the partner app (creates CRM inquiry).
    """
    permission_classes = [IsPartner]

    def post(self, request):
        from core.models import Inquiry
        from core.staff_partner_sync import normalize_mobile

        partner = request.partner
        client_name = (request.data.get('client_name') or '').strip()
        mobile = normalize_mobile(request.data.get('mobile') or '')
        area = (request.data.get('area') or request.data.get('location') or '').strip()

        if not client_name or len(mobile) != 10:
            return Response(
                {'error': 'Valid client name and 10-digit mobile are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inquiry = Inquiry.objects.create(
            name=client_name,
            mobile=mobile,
            message=(
                f'Partner referral from {partner.full_name} ({partner.mobile}). '
                f'Area: {area or "Not specified"}'
            ),
            service_interest='Partner Referral',
            city=area[:100] if area else 'Partner Referral',
            status=Inquiry.InquiryStatus.NEW,
        )

        logger.info('Partner %s referred client %s (%s)', partner.mobile, client_name, mobile)
        return Response(
            {
                'message': 'Referral submitted. Our team will contact the client soon.',
                'inquiry_id': inquiry.id,
            },
            status=status.HTTP_201_CREATED,
        )
