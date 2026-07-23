"""
Booking report clients list + remark APIs.

GET  /api/booking-report-clients/
GET  /api/booking-report-clients/{id}/
GET  /api/booking-report-clients/{id}/remarks/
POST /api/booking-report-clients/{id}/remarks/
PATCH/DELETE /api/booking-report-clients/remarks/{remark_id}/
"""

from django.db.models import Count, Prefetch, Q
from django_filters import rest_framework as django_filters
from rest_framework import filters, mixins, response, status, views, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .booking_report_serializers import (
    BookingReportClientRemarkSerializer,
    BookingReportClientSerializer,
)
from .models import BookingReportClient, BookingReportClientRemark, RemarkType
from .permissions import IsCRMOperationalUser, IsRemarkAdmin
from .remark_views import RemarkHistoryPagination, _log_remark_activity


class BookingReportClientPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class BookingReportClientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    mobile = django_filters.CharFilter(method='filter_mobile')
    number = django_filters.CharFilter(method='filter_mobile')

    class Meta:
        model = BookingReportClient
        fields = ['name', 'mobile', 'number']

    def filter_mobile(self, queryset, name, value):
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        if not digits:
            return queryset.none()
        return queryset.filter(mobile__icontains=digits)


class BookingReportClientViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    List / retrieve booking report clients (imported from Excel).
    Auth: CRM JWT (same as other CRM list APIs).
    """

    serializer_class = BookingReportClientSerializer
    permission_classes = [IsCRMOperationalUser]
    pagination_class = BookingReportClientPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BookingReportClientFilter
    ordering_fields = ['name', 'mobile', 'id', 'created_at', 'remarks_count']
    ordering = ['name', 'id']
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get_queryset(self):
        latest_remarks = Prefetch(
            'remarks',
            queryset=BookingReportClientRemark.objects.select_related('created_by').order_by('-created_at'),
        )
        qs = (
            BookingReportClient.objects.all()
            .annotate(remarks_count=Count('remarks', distinct=True))
            .prefetch_related(latest_remarks)
        )
        q = (
            self.request.query_params.get('q')
            or self.request.query_params.get('search')
            or ''
        ).strip()
        if q:
            digits = ''.join(ch for ch in q if ch.isdigit())
            name_q = Q(name__icontains=q)
            if digits:
                qs = qs.filter(name_q | Q(mobile__icontains=digits))
            else:
                qs = qs.filter(name_q)
        return qs


class BookingReportClientRemarkListCreateView(views.APIView):
    """List + add remarks for one booking-report client (per number/row)."""

    permission_classes = [IsCRMOperationalUser]

    def get(self, request, client_id):
        try:
            client = BookingReportClient.objects.get(pk=client_id)
        except BookingReportClient.DoesNotExist:
            return response.Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        qs = (
            BookingReportClientRemark.objects.filter(client=client)
            .select_related('created_by')
            .order_by('-created_at')
        )
        paginator = RemarkHistoryPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = BookingReportClientRemarkSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, client_id):
        try:
            client = BookingReportClient.objects.get(pk=client_id)
        except BookingReportClient.DoesNotExist:
            return response.Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        text = (request.data.get('remark') or '').strip()
        if not text:
            return response.Response({'error': 'Remark text is required'}, status=status.HTTP_400_BAD_REQUEST)

        remark_type = request.data.get('remark_type') or RemarkType.NOTE
        if remark_type not in RemarkType.values:
            remark_type = RemarkType.NOTE

        entry = BookingReportClientRemark.objects.create(
            client=client,
            remark=text,
            created_by=request.user,
            remark_type=remark_type,
        )
        _log_remark_activity(
            request.user,
            'Added Booking Report Client Remark',
            inquiry_label=f"Booking Report Client #{client.id} ({client.name} / {client.mobile})",
            new_text=text,
        )
        serializer = BookingReportClientRemarkSerializer(entry, context={'request': request})
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingReportClientRemarkDetailView(views.APIView):
    """Update / delete a booking-report client remark (admin)."""

    permission_classes = [IsRemarkAdmin]

    def patch(self, request, pk):
        try:
            entry = BookingReportClientRemark.objects.select_related('client').get(pk=pk)
        except BookingReportClientRemark.DoesNotExist:
            return response.Response({'error': 'Remark not found'}, status=status.HTTP_404_NOT_FOUND)

        new_text = (request.data.get('remark') or '').strip()
        if not new_text:
            return response.Response({'error': 'Remark text is required'}, status=status.HTTP_400_BAD_REQUEST)

        old_text = entry.remark
        entry.remark = new_text
        if 'remark_type' in request.data:
            rt = request.data.get('remark_type')
            if rt in RemarkType.values:
                entry.remark_type = rt
        entry.save(update_fields=['remark', 'remark_type', 'updated_at'])

        _log_remark_activity(
            request.user,
            'Updated Booking Report Client Remark',
            inquiry_label=f"Booking Report Client #{entry.client_id}",
            old_text=old_text,
            new_text=new_text,
        )
        return response.Response(
            BookingReportClientRemarkSerializer(entry, context={'request': request}).data
        )

    def delete(self, request, pk):
        try:
            entry = BookingReportClientRemark.objects.select_related('client').get(pk=pk)
        except BookingReportClientRemark.DoesNotExist:
            return response.Response({'error': 'Remark not found'}, status=status.HTTP_404_NOT_FOUND)

        old_text = entry.remark
        client_id = entry.client_id
        entry.delete()
        _log_remark_activity(
            request.user,
            'Deleted Booking Report Client Remark',
            inquiry_label=f"Booking Report Client #{client_id}",
            new_text=old_text,
        )
        return response.Response(status=status.HTTP_204_NO_CONTENT)
