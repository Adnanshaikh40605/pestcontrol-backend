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
    PartnerUpdateSerializer,
    PartnerFCMSerializer,
    PartnerBookingListSerializer,
    PartnerBookingDetailSerializer,
    PartnerCompleteBookingSerializer,
    PartnerEarningSerializer,
    PartnerProfileStatsSerializer,
)
from .permissions import IsPartner, IsPartnerAdmin
from .utils import generate_partner_tokens
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

        mobile = serializer.validated_data['mobile']
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
            },
            status=status.HTTP_200_OK,
        )


class UpdateFCMTokenAPIView(APIView):
    """
    POST /api/partner/fcm-token/
    Update the device's Firebase Cloud Messaging token for push notifications.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Authentication"],
        summary="Update FCM push notification token",
        description="Send the device FCM token after login to enable push notifications.",
        request=PartnerFCMSerializer,
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    )
    def post(self, request):
        serializer = PartnerFCMSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        request.partner.fcm_token = serializer.validated_data['fcm_token']
        request.partner.save(update_fields=['fcm_token'])

        return Response({"message": "FCM token updated successfully."})


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
            partner=partner,
            partner_status=JobCard.PartnerStatus.PENDING,
        ).select_related('client', 'master_city', 'master_location').order_by('schedule_datetime')

        serializer = PartnerBookingListSerializer(jobs, many=True)
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

        serializer = PartnerBookingListSerializer(jobs, many=True)
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

        serializer = PartnerBookingListSerializer(jobs, many=True)
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

        serializer = PartnerBookingDetailSerializer(job)
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
        available = JobCard.objects.filter(partner=partner, partner_status='pending').count()
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
            job = JobCard.objects.get(id=id, partner=partner)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found or not assigned to you."}, status=404)

        if job.partner_status != JobCard.PartnerStatus.PENDING:
            return Response(
                {"error": f"Cannot accept a booking with status '{job.partner_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.partner_status = JobCard.PartnerStatus.ACCEPTED
        job.is_accepted = True
        job.accepted_at = timezone.now()
        job.status = JobCard.JobStatus.ON_PROCESS
        job.save(update_fields=['partner_status', 'is_accepted', 'accepted_at', 'status'])

        logger.info(f"Partner {partner.full_name} accepted booking #{job.id}")
        return Response({"message": "Booking accepted! Move to Accepted tab."})


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
            job = JobCard.objects.get(id=id, partner=partner)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found or not assigned to you."}, status=404)

        if job.partner_status != JobCard.PartnerStatus.PENDING:
            return Response(
                {"error": f"Cannot reject a booking with status '{job.partner_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get('reason', '')
        job.partner_status = JobCard.PartnerStatus.REJECTED
        job.partner = None  # Unassign from partner
        job.sync_booking_category()
        job.status = job.status_after_technician_removal()
        job.removal_remarks = f"Rejected by partner {partner.full_name}: {reason}"
        job.save(update_fields=['partner_status', 'partner', 'status', 'removal_remarks', 'booking_category'])

        logger.info(f"Partner {partner.full_name} rejected booking #{job.id}. Reason: {reason}")
        return Response({"message": "Booking rejected. Admin will reassign it."})


class StartServiceAPIView(APIView):
    """
    POST /api/partner/bookings/{id}/start/
    Mark service as started.
    """
    permission_classes = [IsPartner]

    @extend_schema(
        tags=["Bookings"],
        summary="Start service",
        description="Mark the service as started. Sets partner_status to 'in_service' and records start time.",
        request=None,
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    )
    def post(self, request, id):
        partner = request.partner
        try:
            job = JobCard.objects.get(id=id, partner=partner)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found or not assigned to you."}, status=404)

        if job.partner_status != JobCard.PartnerStatus.ACCEPTED:
            return Response(
                {"error": f"Can only start an accepted booking. Current status: '{job.partner_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.partner_status = JobCard.PartnerStatus.IN_SERVICE
        job.started_at = timezone.now()
        job.save(update_fields=['partner_status', 'started_at'])

        logger.info(f"Partner {partner.full_name} started service for booking #{job.id}")
        return Response({"message": "Service started! Click 'End Service' when done."})


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
        try:
            job = JobCard.objects.get(id=id, partner=partner)
        except JobCard.DoesNotExist:
            return Response({"error": "Booking not found or not assigned to you."}, status=404)

        if job.partner_status not in [
            JobCard.PartnerStatus.ACCEPTED,
            JobCard.PartnerStatus.IN_SERVICE,
        ]:
            return Response(
                {"error": f"Cannot complete a booking with status '{job.partner_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PartnerCompleteBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        payment_mode = serializer.validated_data['payment_mode']

        # Update job
        job.partner_status = JobCard.PartnerStatus.COMPLETED
        job.status = JobCard.JobStatus.DONE
        job.payment_mode = payment_mode
        job.payment_status = JobCard.PaymentStatus.PAID
        job.completed_at = timezone.now()
        if not job.started_at:
            job.started_at = job.completed_at  # fallback if start was skipped
        job.save()

        # Trigger AMC follow-up / service automation
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
            "message": f"Service completed! Payment via {payment_mode}. Great work! 🎉",
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
    permission_classes = [IsPartner]

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

        return Response({
            "partner": PartnerSerializer(partner).data,
            "stats": {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "accepted_jobs": accepted_jobs,
                "available_jobs": available_jobs,
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
        return Response({
            "message": "Profile updated successfully.",
            "partner": PartnerSerializer(request.partner).data,
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
