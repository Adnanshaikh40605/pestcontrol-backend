"""REST APIs for visits, tasks, leave, expenses, and geo-attendance extensions."""

from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .identity import resolve_profile_from_request
from .operations_models import (
    ExpenseCategory,
    ExpenseClaim,
    FieldVisit,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    StaffTask,
    TaskComment,
)
from .operations_serializers import (
    ExpenseCategorySerializer,
    ExpenseClaimSerializer,
    ExpenseReviewSerializer,
    ExpenseSubmitSerializer,
    FieldVisitSerializer,
    LeaveApplicationSerializer,
    LeaveApplySerializer,
    LeaveBalanceSerializer,
    LeaveReviewSerializer,
    LeaveTypeSerializer,
    StaffTaskSerializer,
    TaskCommentSerializer,
    TaskStatusSerializer,
    VisitCheckInSerializer,
    VisitCheckOutSerializer,
)
from .operations_services import (
    apply_leave,
    end_break,
    review_expense,
    review_leave,
    start_break,
    submit_expense,
    sync_jobcards_to_visits,
    update_task_status,
    visit_check_in,
    visit_check_out,
)
from .permissions import IsCRMTrackingAdmin, IsCRMTrackingViewer, IsPartnerOrCRMTrackingViewer, IsTrackedStaff
from .services import get_active_session
from .views_base import TrackingAPIView


def _profile_or_403(request):
    profile = resolve_profile_from_request(request)
    if profile is None:
        return None, Response({'error': 'Tracking profile not found.'}, status=status.HTTP_403_FORBIDDEN)
    return profile, None


# ---------------------------------------------------------------------------
# Visits
# ---------------------------------------------------------------------------


class MyVisitsAPIView(TrackingAPIView):
    """GET today's visits for logged-in staff (syncs from JobCards)."""

    permission_classes = [IsTrackedStaff]

    def get(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        sync_jobcards_to_visits(profile)
        qs = FieldVisit.objects.filter(
            profile=profile,
            scheduled_at__date=timezone.localdate(),
        ).select_related('jobcard', 'profile')
        return Response(FieldVisitSerializer(qs, many=True).data)


class VisitListCreateAPIView(TrackingAPIView):
    """CRM: list/create visits. Staff: not used."""

    permission_classes = [IsCRMTrackingViewer]

    def get(self, request):
        qs = FieldVisit.objects.select_related('profile', 'jobcard').order_by('-scheduled_at')
        visit_date = request.query_params.get('date')
        visit_status = request.query_params.get('status')
        profile_id = request.query_params.get('profile_id')
        if visit_date:
            qs = qs.filter(scheduled_at__date=visit_date)
        if visit_status:
            qs = qs.filter(status=visit_status)
        if profile_id:
            qs = qs.filter(profile_id=profile_id)
        return Response(FieldVisitSerializer(qs[:200], many=True).data)

    def post(self, request):
        serializer = FieldVisitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        visit = serializer.save(created_by=request.user)
        return Response(FieldVisitSerializer(visit).data, status=status.HTTP_201_CREATED)


class VisitCheckInAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def post(self, request, visit_id):
        profile, err = _profile_or_403(request)
        if err:
            return err
        visit = FieldVisit.objects.filter(id=visit_id, profile=profile).first()
        if not visit:
            return Response({'error': 'Visit not found.'}, status=status.HTTP_404_NOT_FOUND)
        payload = VisitCheckInSerializer(data=request.data)
        if not payload.is_valid():
            return Response({'errors': payload.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            visit = visit_check_in(
                visit,
                latitude=float(payload.validated_data['latitude']),
                longitude=float(payload.validated_data['longitude']),
                accuracy_m=payload.validated_data.get('accuracy_m'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FieldVisitSerializer(visit).data)


class VisitCheckOutAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def post(self, request, visit_id):
        profile, err = _profile_or_403(request)
        if err:
            return err
        visit = FieldVisit.objects.filter(id=visit_id, profile=profile).first()
        if not visit:
            return Response({'error': 'Visit not found.'}, status=status.HTTP_404_NOT_FOUND)
        payload = VisitCheckOutSerializer(data=request.data)
        if not payload.is_valid():
            return Response({'errors': payload.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            visit = visit_check_out(
                visit,
                latitude=float(payload.validated_data['latitude']),
                longitude=float(payload.validated_data['longitude']),
                notes=payload.validated_data.get('notes', ''),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FieldVisitSerializer(visit).data)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class MyTasksAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def get(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        qs = StaffTask.objects.filter(assigned_to=profile).exclude(
            status=StaffTask.Status.CANCELLED,
        ).order_by('-created_at')
        task_status = request.query_params.get('status')
        if task_status:
            qs = qs.filter(status=task_status)
        return Response(StaffTaskSerializer(qs[:100], many=True).data)


class TaskListCreateAPIView(TrackingAPIView):
    permission_classes = [IsCRMTrackingViewer]

    def get(self, request):
        qs = StaffTask.objects.select_related('assigned_to').order_by('-created_at')
        assignee = request.query_params.get('assigned_to')
        task_status = request.query_params.get('status')
        if assignee:
            qs = qs.filter(assigned_to_id=assignee)
        if task_status:
            qs = qs.filter(status=task_status)
        return Response(StaffTaskSerializer(qs[:200], many=True).data)

    def post(self, request):
        serializer = StaffTaskSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        task = serializer.save(created_by=request.user)
        return Response(StaffTaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskStatusAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def patch(self, request, task_id):
        profile, err = _profile_or_403(request)
        if err:
            return err
        task = StaffTask.objects.filter(id=task_id, assigned_to=profile).first()
        if not task:
            return Response({'error': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)
        payload = TaskStatusSerializer(data=request.data)
        if not payload.is_valid():
            return Response({'errors': payload.errors}, status=status.HTTP_400_BAD_REQUEST)
        data = payload.validated_data
        try:
            task = update_task_status(
                task,
                new_status=data['status'],
                latitude=float(data['latitude']) if data.get('latitude') is not None else None,
                longitude=float(data['longitude']) if data.get('longitude') is not None else None,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StaffTaskSerializer(task).data)


class TaskCommentAPIView(TrackingAPIView):
    permission_classes = [IsPartnerOrCRMTrackingViewer]

    def post(self, request, task_id):
        profile = resolve_profile_from_request(request)
        task = StaffTask.objects.filter(id=task_id).first()
        if not task:
            return Response({'error': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)
        if profile and task.assigned_to_id != profile.id:
            return Response({'error': 'Not your task.'}, status=status.HTTP_403_FORBIDDEN)
        body = request.data.get('body', '').strip()
        if not body:
            return Response({'error': 'body is required.'}, status=status.HTTP_400_BAD_REQUEST)
        comment = TaskComment.objects.create(
            task=task,
            body=body,
            author=request.user if request.user.is_authenticated and not profile else None,
            profile=profile,
        )
        return Response(TaskCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------


class LeaveBalanceAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def get(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        year = int(request.query_params.get('year', timezone.localdate().year))
        qs = LeaveBalance.objects.filter(profile=profile, year=year).select_related('leave_type')
        return Response(LeaveBalanceSerializer(qs, many=True).data)


class LeaveApplyAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        payload = LeaveApplySerializer(data=request.data)
        if not payload.is_valid():
            return Response({'errors': payload.errors}, status=status.HTTP_400_BAD_REQUEST)
        leave_type = LeaveType.objects.filter(
            id=payload.validated_data['leave_type_id'], is_active=True,
        ).first()
        if not leave_type:
            return Response({'error': 'Invalid leave type.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            app = apply_leave(
                profile,
                leave_type=leave_type,
                start_date=payload.validated_data['start_date'],
                end_date=payload.validated_data['end_date'],
                reason=payload.validated_data['reason'],
                half_day=payload.validated_data['half_day'],
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveApplicationsAPIView(TrackingAPIView):
    permission_classes = [IsPartnerOrCRMTrackingViewer]

    def get(self, request):
        profile = resolve_profile_from_request(request)
        if profile:
            qs = LeaveApplication.objects.filter(profile=profile)
        else:
            qs = LeaveApplication.objects.all()
        app_status = request.query_params.get('status')
        if app_status:
            qs = qs.filter(status=app_status)
        qs = qs.select_related('profile', 'leave_type').order_by('-created_at')[:200]
        return Response(LeaveApplicationSerializer(qs, many=True).data)


class LeaveReviewAPIView(TrackingAPIView):
    permission_classes = [IsCRMTrackingAdmin]

    def patch(self, request, application_id):
        app = LeaveApplication.objects.filter(id=application_id).first()
        if not app:
            return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
        payload = LeaveReviewSerializer(data=request.data)
        if not payload.is_valid():
            return Response({'errors': payload.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            app = review_leave(
                app,
                approved=payload.validated_data['approved'],
                reviewer=request.user,
                comment=payload.validated_data.get('comment', ''),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveApplicationSerializer(app).data)


class LeaveTypesAPIView(TrackingAPIView):
    permission_classes = [IsPartnerOrCRMTrackingViewer]

    def get(self, request):
        qs = LeaveType.objects.filter(is_active=True)
        return Response(LeaveTypeSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------


class ExpenseCategoriesAPIView(TrackingAPIView):
    permission_classes = [IsPartnerOrCRMTrackingViewer]

    def get(self, request):
        qs = ExpenseCategory.objects.filter(is_active=True)
        return Response(ExpenseCategorySerializer(qs, many=True).data)


class MyExpensesAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def get(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        qs = ExpenseClaim.objects.filter(profile=profile).select_related('category').order_by('-expense_date')
        return Response(ExpenseClaimSerializer(qs[:100], many=True).data)

    def post(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        payload = ExpenseSubmitSerializer(data=request.data)
        if not payload.is_valid():
            return Response({'errors': payload.errors}, status=status.HTTP_400_BAD_REQUEST)
        category = ExpenseCategory.objects.filter(
            id=payload.validated_data['category_id'], is_active=True,
        ).first()
        if not category:
            return Response({'error': 'Invalid category.'}, status=status.HTTP_400_BAD_REQUEST)

        distance_km = None
        amount = payload.validated_data.get('amount')
        session = get_active_session(profile)
        if payload.validated_data.get('use_gps_distance') and session:
            distance_km = session.total_distance_km

        try:
            claim = submit_expense(
                profile,
                category=category,
                expense_date=payload.validated_data['expense_date'],
                amount=amount or Decimal('0'),
                description=payload.validated_data.get('description', ''),
                distance_km=distance_km,
                session=session,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class ExpenseListAPIView(TrackingAPIView):
    permission_classes = [IsCRMTrackingViewer]

    def get(self, request):
        qs = ExpenseClaim.objects.select_related('profile', 'category').order_by('-expense_date')
        claim_status = request.query_params.get('status')
        if claim_status:
            qs = qs.filter(status=claim_status)
        return Response(ExpenseClaimSerializer(qs[:200], many=True).data)


class ExpenseReviewAPIView(TrackingAPIView):
    permission_classes = [IsCRMTrackingAdmin]

    def patch(self, request, claim_id):
        claim = ExpenseClaim.objects.filter(id=claim_id).first()
        if not claim:
            return Response({'error': 'Claim not found.'}, status=status.HTTP_404_NOT_FOUND)
        payload = ExpenseReviewSerializer(data=request.data)
        if not payload.is_valid():
            return Response({'errors': payload.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            claim = review_expense(
                claim,
                approved=payload.validated_data['approved'],
                reviewer=request.user,
                comment=payload.validated_data.get('comment', ''),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseClaimSerializer(claim).data)


# ---------------------------------------------------------------------------
# Geo-Attendance — breaks
# ---------------------------------------------------------------------------


class BreakStartAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        try:
            brk = start_break(
                profile,
                latitude=request.data.get('latitude'),
                longitude=request.data.get('longitude'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        from .operations_serializers import AttendanceBreakSerializer
        return Response(AttendanceBreakSerializer(brk).data, status=status.HTTP_201_CREATED)


class BreakEndAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def post(self, request):
        profile, err = _profile_or_403(request)
        if err:
            return err
        try:
            brk = end_break(profile)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        from .operations_serializers import AttendanceBreakSerializer
        return Response(AttendanceBreakSerializer(brk).data)


# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------


class VisitPhotoUploadAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def post(self, request, visit_id):
        profile, err = _profile_or_403(request)
        if err:
            return err
        visit = FieldVisit.objects.filter(id=visit_id, profile=profile).first()
        if not visit:
            return Response({'error': 'Visit not found.'}, status=status.HTTP_404_NOT_FOUND)
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'image file required.'}, status=status.HTTP_400_BAD_REQUEST)
        from .operations_models import VisitPhoto
        photo = VisitPhoto.objects.create(
            visit=visit,
            image=image,
            photo_type=request.data.get('photo_type', VisitPhoto.PhotoType.SITE),
            caption=request.data.get('caption', ''),
        )
        return Response({'id': photo.id, 'url': photo.image.url}, status=status.HTTP_201_CREATED)


class ExpenseReceiptUploadAPIView(TrackingAPIView):
    permission_classes = [IsTrackedStaff]

    def post(self, request, claim_id):
        profile, err = _profile_or_403(request)
        if err:
            return err
        claim = ExpenseClaim.objects.filter(id=claim_id, profile=profile).first()
        if not claim:
            return Response({'error': 'Claim not found.'}, status=status.HTTP_404_NOT_FOUND)
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'image file required.'}, status=status.HTTP_400_BAD_REQUEST)
        from .operations_models import ExpenseReceipt
        receipt = ExpenseReceipt.objects.create(
            claim=claim,
            image=image,
            caption=request.data.get('caption', ''),
        )
        return Response({'id': receipt.id, 'url': receipt.image.url}, status=status.HTTP_201_CREATED)


class GeofenceListAPIView(TrackingAPIView):
    permission_classes = [IsCRMTrackingViewer]

    def get(self, request):
        from .operations_models import GeofenceZone
        from .operations_serializers import GeofenceZoneSerializer
        qs = GeofenceZone.objects.filter(is_active=True)
        return Response(GeofenceZoneSerializer(qs, many=True).data)
