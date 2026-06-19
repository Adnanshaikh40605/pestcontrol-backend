"""Staff Tracking APIs — mobile (Flutter) + CRM dashboard."""

import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.auth import CustomTokenObtainPairSerializer
from core.staff_partner_sync import normalize_mobile
from partner.models import Partner
from partner.serializers import PartnerSerializer
from partner.utils import PartnerTokenError, generate_partner_tokens, refresh_partner_tokens

from .identity import resolve_profile_from_request
from .models import AttendanceSession, LocationPing, TrackingConsent, TrackingProfile, TrackingSettings
from .permissions import IsCRMTrackingAdmin, IsCRMTrackingViewer, IsTrackedStaff
from .serializers import (
    AttendanceSessionSerializer,
    GPSPointSerializer,
    LiveStaffSerializer,
    LocationPingBatchSerializer,
    LocationPingSerializer,
    MeStatusSerializer,
    TrackingLoginSerializer,
    TrackingProfileSerializer,
    TrackingSettingsSerializer,
)
from .services import (
    check_in,
    check_out,
    compute_session_distance,
    get_active_session,
    get_last_ping,
    record_ping,
    record_ping_batch,
    staff_live_status,
)
from .views_base import TrackingAPIView, TrackingPublicAPIView

logger = logging.getLogger(__name__)


def _client_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _build_me_payload(profile: TrackingProfile) -> dict:
    session = get_active_session(profile)
    last_ping = get_last_ping(profile)
    settings = TrackingSettings.get_solo()
    return {
        'profile': TrackingProfileSerializer(profile).data,
        'has_consent': TrackingConsent.objects.filter(profile=profile).exists(),
        'is_checked_in': session is not None,
        'active_session': AttendanceSessionSerializer(session).data if session else None,
        'settings': TrackingSettingsSerializer(settings).data,
        'last_ping': LocationPingSerializer(last_ping).data if last_ping else None,
    }


class LoginAPIView(TrackingPublicAPIView):
    """POST /api/staff-tracking/auth/login/ — Partner or CRM field staff login."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TrackingLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        mobile = normalize_mobile(serializer.validated_data['mobile'])
        password = serializer.validated_data['password']

        # 1) Partner (primary field staff)
        partner = Partner.objects.filter(mobile=mobile).first()
        if partner:
            if not partner.is_active:
                return Response({'error': 'Account deactivated.'}, status=status.HTTP_403_FORBIDDEN)
            if partner.check_password(password):
                tokens = generate_partner_tokens(partner)
                return Response({
                    **tokens,
                    'auth_type': 'partner',
                    'partner': PartnerSerializer(partner).data,
                    'is_app_approved': partner.is_app_approved,
                })

        # 2) CRM User (field staff with technician row)
        User = get_user_model()
        user = User.objects.filter(username=mobile).first()
        if user and user.check_password(password) and user.is_active:
            token_serializer = CustomTokenObtainPairSerializer(
                data={'username': mobile, 'password': password},
                context={'request': request},
            )
            if token_serializer.is_valid():
                data = token_serializer.validated_data
                return Response({
                    'access': data['access'],
                    'refresh': data['refresh'],
                    'auth_type': 'crm',
                    'user_id': data.get('user_id'),
                    'username': data.get('username'),
                    'role': data.get('role'),
                    'first_name': data.get('first_name'),
                    'last_name': data.get('last_name'),
                })

        return Response({'error': 'Invalid mobile or password.'}, status=status.HTTP_401_UNAUTHORIZED)


class RefreshTokenAPIView(TrackingPublicAPIView):
    """POST /api/staff-tracking/auth/refresh/ — refresh partner or CRM token."""

    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.data.get('refresh')
        auth_type = request.data.get('auth_type', 'partner')

        if not refresh:
            return Response({'error': 'refresh token required'}, status=status.HTTP_400_BAD_REQUEST)

        if auth_type == 'partner':
            try:
                tokens = refresh_partner_tokens(refresh)
                return Response({**tokens, 'auth_type': 'partner'})
            except PartnerTokenError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        from rest_framework_simplejwt.views import TokenRefreshView
        from core.auth import CustomTokenRefreshSerializer
        serializer = CustomTokenRefreshSerializer(data={'refresh': refresh})
        if serializer.is_valid():
            return Response({
                'access': str(serializer.validated_data['access']),
                'refresh': request.data.get('refresh'),
                'auth_type': 'crm',
            })
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class MeAPIView(TrackingAPIView):
    """GET /api/staff-tracking/me/ — current staff status."""

    permission_classes = [IsTrackedStaff]

    def get(self, request):
        profile = resolve_profile_from_request(request)
        if profile is None:
            return Response(
                {'error': 'No technician profile linked to this account.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_build_me_payload(profile))


class ConsentAPIView(TrackingAPIView):
    """POST /api/staff-tracking/consent/ — record GPS tracking consent."""

    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile = resolve_profile_from_request(request)
        if profile is None:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        from .identity import ensure_consent
        ensure_consent(profile, ip_address=_client_ip(request))
        return Response({'message': 'Consent recorded.', 'has_consent': True})


class CheckInAPIView(TrackingAPIView):
    """POST /api/staff-tracking/attendance/checkin/"""

    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile = resolve_profile_from_request(request)
        if profile is None or not profile.tracking_enabled:
            return Response({'error': 'Tracking not enabled for this account.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = GPSPointSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        session = check_in(
            profile,
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            accuracy_m=data.get('accuracy_m'),
            ip_address=_client_ip(request),
        )
        return Response({
            'message': 'Checked in successfully.',
            'session': AttendanceSessionSerializer(session).data,
        })


class CheckOutAPIView(TrackingAPIView):
    """POST /api/staff-tracking/attendance/checkout/"""

    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile = resolve_profile_from_request(request)
        if profile is None:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = GPSPointSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            session = check_out(
                profile,
                latitude=float(data['latitude']),
                longitude=float(data['longitude']),
                accuracy_m=data.get('accuracy_m'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Checked out successfully.',
            'session': AttendanceSessionSerializer(session).data,
        })


class LocationPingAPIView(TrackingAPIView):
    """POST /api/staff-tracking/location/ping/"""

    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile = resolve_profile_from_request(request)
        if profile is None:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = GPSPointSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            ping = record_ping(
                profile,
                latitude=float(data['latitude']),
                longitude=float(data['longitude']),
                recorded_at=data.get('recorded_at'),
                accuracy_m=data.get('accuracy_m'),
                altitude_m=data.get('altitude_m'),
                speed_mps=data.get('speed_mps'),
                heading=data.get('heading'),
                battery_percent=data.get('battery_percent'),
                is_moving=data.get('is_moving', True),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LocationPingSerializer(ping).data, status=status.HTTP_201_CREATED)


class LocationBatchAPIView(TrackingAPIView):
    """POST /api/staff-tracking/location/batch/ — offline sync."""

    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile = resolve_profile_from_request(request)
        if profile is None:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LocationPingBatchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        pings = []
        for item in serializer.validated_data['pings']:
            pings.append({
                'latitude': float(item['latitude']),
                'longitude': float(item['longitude']),
                'recorded_at': item.get('recorded_at'),
                'accuracy_m': item.get('accuracy_m'),
                'altitude_m': item.get('altitude_m'),
                'speed_mps': item.get('speed_mps'),
                'heading': item.get('heading'),
                'battery_percent': item.get('battery_percent'),
                'is_moving': item.get('is_moving', True),
            })

        created = record_ping_batch(profile, pings)
        return Response({'synced': created, 'total': len(pings)})


class MyAttendanceAPIView(TrackingAPIView):
    """GET /api/staff-tracking/me/attendance/"""

    permission_classes = [IsTrackedStaff]

    def get(self, request):
        profile = resolve_profile_from_request(request)
        if profile is None:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = AttendanceSession.objects.filter(profile=profile).order_by('-date')[:30]
        return Response(AttendanceSessionSerializer(qs, many=True).data)


# ── CRM Dashboard APIs ────────────────────────────────────────────────────────


class CRMBaseAPIView(APIView):
    """CRM JWT auth — uses default SimpleJWT + IsCRMTrackingViewer."""
    permission_classes = [IsCRMTrackingViewer]


class LiveStaffAPIView(CRMBaseAPIView):
    """GET /api/staff-tracking/live/ — all staff with last known location."""

    def get(self, request):
        profiles = (
            TrackingProfile.objects.filter(is_active=True, tracking_enabled=True)
            .select_related('technician')
        )
        results = []
        today = timezone.localdate()

        for profile in profiles:
            last_ping = get_last_ping(profile)
            session = get_active_session(profile, today)
            status_label = staff_live_status(profile)
            distance = None
            if session:
                distance = compute_session_distance(session)

            results.append({
                'profile_id': profile.id,
                'technician_id': profile.technician_id,
                'name': profile.technician.name,
                'mobile': profile.technician.mobile,
                'city': profile.technician.city,
                'status': status_label,
                'latitude': last_ping.latitude if last_ping else None,
                'longitude': last_ping.longitude if last_ping else None,
                'last_ping_at': last_ping.recorded_at if last_ping else None,
                'battery_percent': last_ping.battery_percent if last_ping else None,
                'check_in_at': session.check_in_at if session else None,
                'distance_today_km': distance,
            })

        serializer = LiveStaffSerializer(results, many=True)
        return Response(serializer.data)


class StaffDirectoryAPIView(CRMBaseAPIView):
    """GET /api/staff-tracking/staff/ — tracking-enabled staff list."""

    def get(self, request):
        qs = TrackingProfile.objects.filter(is_active=True).select_related('technician')
        city = request.query_params.get('city')
        if city:
            qs = qs.filter(technician__city__icontains=city)
        return Response(TrackingProfileSerializer(qs, many=True).data)


class AttendanceTodayAPIView(CRMBaseAPIView):
    """GET /api/staff-tracking/attendance/today/"""

    def get(self, request):
        today = timezone.localdate()
        sessions = (
            AttendanceSession.objects.filter(date=today)
            .select_related('profile__technician')
            .order_by('-check_in_at')
        )
        return Response(AttendanceSessionSerializer(sessions, many=True).data)


class AttendanceReportAPIView(CRMBaseAPIView):
    """GET /api/staff-tracking/attendance/report/?from=&to="""

    def get(self, request):
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')
        qs = AttendanceSession.objects.select_related('profile__technician').order_by('-date')

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        page_size = min(int(request.query_params.get('page_size', 50)), 200)
        qs = qs[:page_size]
        return Response(AttendanceSessionSerializer(qs, many=True).data)


class LocationHistoryAPIView(CRMBaseAPIView):
    """GET /api/staff-tracking/location/history/<technician_id>/?date="""

    def get(self, request, technician_id: int):
        target_date = request.query_params.get('date') or str(timezone.localdate())
        profile = TrackingProfile.objects.filter(technician_id=technician_id).first()
        if profile is None:
            return Response({'error': 'Staff not found.'}, status=status.HTTP_404_NOT_FOUND)

        pings = LocationPing.objects.filter(
            profile=profile,
            recorded_at__date=target_date,
        ).order_by('recorded_at')

        session = AttendanceSession.objects.filter(profile=profile, date=target_date).first()
        return Response({
            'technician_id': technician_id,
            'name': profile.technician.name,
            'date': target_date,
            'session': AttendanceSessionSerializer(session).data if session else None,
            'pings': LocationPingSerializer(pings, many=True).data,
            'distance_km': compute_session_distance(session) if session else None,
        })


class DistanceReportAPIView(CRMBaseAPIView):
    """GET /api/staff-tracking/location/distance/?date="""

    def get(self, request):
        target_date = request.query_params.get('date') or timezone.localdate()
        sessions = AttendanceSession.objects.filter(date=target_date).select_related('profile__technician')
        rows = []
        for session in sessions:
            distance = session.total_distance_km or compute_session_distance(session)
            rows.append({
                'technician_id': session.profile.technician_id,
                'name': session.profile.technician.name,
                'date': str(session.date),
                'distance_km': distance,
                'check_in_at': session.check_in_at,
                'check_out_at': session.check_out_at,
            })
        return Response(rows)


class SettingsAPIView(CRMBaseAPIView):
    """GET/PATCH /api/staff-tracking/settings/"""

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsCRMTrackingAdmin()]
        return [IsCRMTrackingViewer()]

    def get(self, request):
        settings = TrackingSettings.get_solo()
        return Response(TrackingSettingsSerializer(settings).data)

    def patch(self, request):
        settings = TrackingSettings.get_solo()
        serializer = TrackingSettingsSerializer(settings, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)
