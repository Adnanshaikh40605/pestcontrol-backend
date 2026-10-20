"""API for DeepCleaning99.com booking inquiries — isolated from pest Website Leads."""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Case, Count, F, Max, Prefetch, Q, Value, When
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, response, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .deepcleaning_serializers import (
    DeepCleaningBookingSerializer,
    DeepCleaningInquiryRemarkSerializer,
    DeepCleaningInquirySerializer,
    DeepCleaningRateSerializer,
    DeepCleaningTechnicianSerializer,
    website_catalog,
)
from .deepcleaning_services import DeepCleaningBookingService, DeepCleaningInquiryService
from .inquiry_filters import InquiryListCountsMixin
from .models import (
    DeepCleaningBooking,
    DeepCleaningInquiry,
    DeepCleaningInquiryRemark,
    DeepCleaningRate,
    DeepCleaningTechnician,
)
from .auth import WebsiteInquiryUpsertThrottle
from .permissions import IsCRMOperationalUser, IsRemarkAdmin
from .remark_views import RemarkHistoryPagination, _log_remark_activity

logger = logging.getLogger(__name__)


class DeepCleaningInquiryViewSet(InquiryListCountsMixin, viewsets.ModelViewSet):
    """
    Public POST creates a DeepCleaning99 inquiry.
    Authenticated CRM staff list/update/mark-read.
    """

    queryset = DeepCleaningInquiry.objects.all()
    serializer_class = DeepCleaningInquirySerializer
    permission_classes = [IsCRMOperationalUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    filterset_fields = ['status', 'is_read', 'city', 'service']
    search_fields = ['name', 'mobile', 'city', 'area', 'service', 'package_name', 'address']
    ordering_fields = ['created_at', 'updated_at', 'preferred_date']
    ordering = ['-created_at', '-id']
    date_filter_field = 'created_at'
    search_fields_list = (
        'name', 'mobile', 'city', 'area', 'service', 'package_name', 'address', 'notes',
    )

    def get_authenticators(self):
        if getattr(self, 'action', None) in ('create', 'upsert'):
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if getattr(self, 'action', None) in ('create', 'upsert'):
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        qs = DeepCleaningInquiry.objects.select_related('booking').annotate(
            remark_count=Count('remarks', distinct=True),
            last_remark_at=Max('remarks__updated_at'),
        ).annotate(
            needs_comment_update=Case(
                When(last_remark_at__isnull=True, then=Value(True)),
                When(last_remark_at__lt=F('updated_at'), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).prefetch_related(
            Prefetch(
                'remarks',
                queryset=DeepCleaningInquiryRemark.objects.select_related('created_by').order_by('-created_at')[:1],
                to_attr='_latest_remarks',
            )
        )
        self.queryset = qs
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        try:
            inquiry = DeepCleaningInquiryService.create_inquiry(request.data, user=None)
            data = DeepCleaningInquirySerializer(inquiry, context={'request': request}).data
            return response.Response(data, status=status.HTTP_201_CREATED)
        except ValidationError as exc:
            details = getattr(exc, 'message_dict', None) or getattr(exc, 'messages', None) or str(exc)
            return response.Response(
                {'error': 'Validation failed', 'details': details},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error('DeepCleaning inquiry create failed: %s', exc, exc_info=True)
            return response.Response(
                {'error': 'Could not save booking request. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=['post'],
        url_path='upsert',
        throttle_classes=[WebsiteInquiryUpsertThrottle],
    )
    def upsert(self, request):
        """Public silent capture. One lead per booking session, as soon as mobile is valid."""
        try:
            inquiry, created = DeepCleaningInquiryService.upsert_inquiry(request.data, user=None)
            data = DeepCleaningInquirySerializer(inquiry, context={'request': request}).data
            return response.Response(
                data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        except ValidationError as exc:
            details = getattr(exc, 'message_dict', None) or getattr(exc, 'messages', None) or str(exc)
            return response.Response(
                {'error': 'Validation failed', 'details': details},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error('DeepCleaning inquiry upsert failed: %s', exc, exc_info=True)
            return response.Response(
                {'error': 'Could not save booking request. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        """Staff may update status / is_read only (keep booking payload intact)."""
        instance = self.get_object()
        allowed = {}
        if 'status' in request.data:
            status_value = str(request.data.get('status') or '').strip()
            valid = {c.value for c in DeepCleaningInquiry.InquiryStatus}
            if status_value not in valid:
                return response.Response(
                    {'error': 'Invalid status'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            allowed['status'] = status_value
        if 'is_read' in request.data:
            allowed['is_read'] = bool(request.data.get('is_read'))
        if not allowed:
            return response.Response(
                {'error': 'Only status and is_read can be updated'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for key, value in allowed.items():
            setattr(instance, key, value)
        instance.save(update_fields=[*allowed.keys(), 'updated_at'])
        return response.Response(
            DeepCleaningInquirySerializer(instance, context={'request': request}).data
        )

    @action(detail=True, methods=['post'], url_path='mark_as_read')
    def mark_as_read(self, request, pk=None):
        updated = DeepCleaningInquiry.objects.filter(pk=pk).update(is_read=True)
        if not updated:
            return response.Response({'error': 'Inquiry not found'}, status=status.HTTP_404_NOT_FOUND)
        return response.Response({'status': 'marked as read', 'id': int(pk), 'is_read': True})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        count = DeepCleaningInquiry.objects.filter(is_read=False).update(is_read=True)
        return response.Response({'status': 'success', 'updated': count})

    @action(detail=True, methods=['post'], url_path='confirm-booking')
    def confirm_booking(self, request, pk=None):
        inquiry = self.get_object()
        try:
            booking, created = DeepCleaningBookingService.confirm_inquiry(inquiry, request.user)
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, 'messages', None) else str(exc)
            return response.Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        payload = DeepCleaningBookingSerializer(booking, context={'request': request}).data
        return response.Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DeepCleaningInquiryRemarkListCreateView(views.APIView):
    permission_classes = [IsCRMOperationalUser]

    def get(self, request, inquiry_id):
        try:
            inquiry = DeepCleaningInquiry.objects.get(pk=inquiry_id)
        except DeepCleaningInquiry.DoesNotExist:
            return response.Response({'error': 'Inquiry not found'}, status=status.HTTP_404_NOT_FOUND)

        qs = (
            DeepCleaningInquiryRemark.objects.filter(inquiry=inquiry)
            .select_related('created_by')
            .order_by('-created_at')
        )
        paginator = RemarkHistoryPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = DeepCleaningInquiryRemarkSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, inquiry_id):
        try:
            inquiry = DeepCleaningInquiry.objects.get(pk=inquiry_id)
        except DeepCleaningInquiry.DoesNotExist:
            return response.Response({'error': 'Inquiry not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            entry = DeepCleaningInquiryService.add_remark(
                inquiry,
                request.data.get('remark') or '',
                user=request.user,
            )
        except ValidationError as exc:
            return response.Response(
                {'error': str(exc.messages[0] if getattr(exc, 'messages', None) else exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _log_remark_activity(
            request.user,
            'Added DeepCleaning99 Inquiry Remark',
            inquiry_label=f"DeepCleaning99 #{inquiry.id} ({inquiry.name})",
            new_text=entry.remark,
        )
        payload = dict(
            DeepCleaningInquiryRemarkSerializer(entry, context={'request': request}).data
        )
        payload['needs_comment_update'] = False
        payload['comment_status'] = 'added'
        payload['inquiry_id'] = inquiry.id
        return response.Response(payload, status=status.HTTP_201_CREATED)


class DeepCleaningInquiryRemarkDetailView(views.APIView):
    permission_classes = [IsRemarkAdmin]

    def patch(self, request, pk):
        try:
            entry = DeepCleaningInquiryRemark.objects.select_related('inquiry').get(pk=pk)
        except DeepCleaningInquiryRemark.DoesNotExist:
            return response.Response({'error': 'Remark not found'}, status=status.HTTP_404_NOT_FOUND)

        new_text = (request.data.get('remark') or '').strip()
        if not new_text:
            return response.Response({'error': 'Remark text is required'}, status=status.HTTP_400_BAD_REQUEST)

        old_text = entry.remark
        entry.remark = new_text
        entry.save(update_fields=['remark', 'updated_at'])
        DeepCleaningInquiry.objects.filter(pk=entry.inquiry_id).update(updated_at=entry.updated_at)
        _log_remark_activity(
            request.user,
            'Edited DeepCleaning99 Inquiry Remark',
            inquiry_label=f"DeepCleaning99 #{entry.inquiry_id}",
            new_text=new_text,
            old_text=old_text,
        )
        return response.Response(
            DeepCleaningInquiryRemarkSerializer(entry, context={'request': request}).data
        )


def _service_error(exc: ValidationError):
    message = exc.messages[0] if getattr(exc, 'messages', None) else str(exc)
    return response.Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)


class DeepCleaningTechnicianViewSet(viewsets.ModelViewSet):
    """CRM directory for Deep Cleaning technicians."""

    queryset = DeepCleaningTechnician.objects.all()
    serializer_class = DeepCleaningTechnicianSerializer
    permission_classes = [IsCRMOperationalUser]
    pagination_class = None
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'mobile', 'location', 'address']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        qs = DeepCleaningTechnician.objects.all()
        available = str(self.request.query_params.get('available') or '').lower()
        if available in ('1', 'true', 'yes'):
            qs = qs.filter(
                is_active=True,
                presence_status=DeepCleaningTechnician.PresenceStatus.ACTIVE,
            )
        service = (self.request.query_params.get('service') or '').strip()
        city = (self.request.query_params.get('city') or '').strip()
        if service:
            qs = qs.filter(services__contains=[service])
        if city:
            qs = qs.filter(cities__contains=[city])
        return qs


class DeepCleaningBookingViewSet(viewsets.ModelViewSet):
    """Pending, On Process, and Done bookings for Deep Cleaning."""

    queryset = DeepCleaningBooking.objects.select_related('technician', 'inquiry')
    serializer_class = DeepCleaningBookingSerializer
    permission_classes = [IsCRMOperationalUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'city', 'service']
    search_fields = ['code', 'name', 'mobile', 'address', 'service', 'city', 'technician__name']
    ordering_fields = ['created_at', 'preferred_date', 'id']
    ordering = ['-created_at', '-id']

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        count_qs = DeepCleaningBooking.objects.all()
        search = (request.query_params.get('search') or '').strip()
        if search:
            count_qs = count_qs.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
                | Q(mobile__icontains=search)
                | Q(address__icontains=search)
                | Q(service__icontains=search)
                | Q(city__icontains=search)
                | Q(technician__name__icontains=search)
            )
        city = (request.query_params.get('city') or '').strip()
        if city:
            count_qs = count_qs.filter(city=city)
        counts = {choice: 0 for choice, _label in DeepCleaningBooking.Status.choices}
        for row in count_qs.values('status').annotate(total=Count('id')):
            counts[row['status']] = row['total']
        counts['all'] = sum(counts[choice] for choice, _label in DeepCleaningBooking.Status.choices)
        if isinstance(resp.data, dict):
            resp.data['status_counts'] = counts
        return resp

    def _act(self, booking, method):
        try:
            updated = method(booking)
        except ValidationError as exc:
            return _service_error(exc)
        return response.Response(
            DeepCleaningBookingSerializer(updated, context={'request': self.request}).data
        )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        booking = self.get_object()
        technician_id = request.data.get('technician_id')
        if not technician_id:
            return response.Response({'error': 'technician_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            technician = DeepCleaningTechnician.objects.get(pk=technician_id)
        except (DeepCleaningTechnician.DoesNotExist, ValueError, TypeError):
            return response.Response({'error': 'Technician not found'}, status=status.HTTP_404_NOT_FOUND)
        return self._act(booking, lambda row: DeepCleaningBookingService.assign(row, technician))

    @action(detail=True, methods=['post'])
    def unassign(self, request, pk=None):
        return self._act(self.get_object(), DeepCleaningBookingService.unassign)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        return self._act(self.get_object(), DeepCleaningBookingService.complete)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        return self._act(self.get_object(), DeepCleaningBookingService.cancel)


class DeepCleaningRateViewSet(viewsets.ModelViewSet):
    """CRM master for Deepcleaning99 prices. Public catalog is read-only."""

    queryset = DeepCleaningRate.objects.all()
    serializer_class = DeepCleaningRateSerializer
    permission_classes = [IsCRMOperationalUser]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['segment', 'service', 'is_active']
    search_fields = ['code', 'service', 'package_name', 'scope_note']
    ordering_fields = ['sort_order', 'code', 'job_amount', 'updated_at']
    ordering = ['sort_order', 'code']

    def get_authenticators(self):
        if getattr(self, 'action', None) == 'catalog':
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if getattr(self, 'action', None) == 'catalog':
            return [permissions.AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='catalog')
    def catalog(self, request):
        rates = DeepCleaningRate.objects.filter(is_active=True).order_by('sort_order', 'code')
        return response.Response(website_catalog(rates))
