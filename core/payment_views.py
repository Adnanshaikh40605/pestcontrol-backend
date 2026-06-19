"""API views for pending payment collection and history."""
import logging
from datetime import datetime, time

from django.db.models import Q, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import decorators, filters, status, viewsets
from rest_framework.response import Response

from .models import ActivityLog, BookingPayment, JobCard
from .payment_utils import payment_status_label
from .permissions import IsCRMOperationalUser
from .serializers import BookingPaymentSerializer, CollectPaymentSerializer, JobCardSerializer
from .services import JobCardService

logger = logging.getLogger(__name__)


def billable_outstanding_queryset(request=None):
    """
    Done main bookings with an outstanding balance.
    Excludes AMC follow-ups, complaint/revisit calls, and included AMC visits.
    """
    qs = (
        JobCard.objects.filter(
            pending_amount__gt=0,
            status=JobCard.JobStatus.DONE,
        )
        .exclude(
            Q(included_in_amc=True)
            | Q(is_followup_visit=True)
            | Q(is_complaint_call=True)
            | Q(booking_category=JobCard.BookingCategory.AMC_FOLLOWUP)
            | Q(booking_category=JobCard.BookingCategory.COMPLAINT_CALL)
            | Q(booking_type=JobCard.BookingType.AMC_FOLLOWUP)
            | Q(booking_type=JobCard.BookingType.COMPLAINT_CALL)
        )
        .select_related('client', 'master_city', 'created_by', 'done_by')
        .prefetch_related('payment_records')
    )

    if request is None:
        return qs

    params = request.query_params
    payment_status = params.get('payment_status', '').strip()
    if payment_status == 'Fully Paid':
        qs = qs.filter(pending_amount=0)
    elif payment_status == 'Partially Paid':
        qs = qs.filter(payment_status=JobCard.PaymentStatus.PARTIALLY_PAID)
    elif payment_status == 'Pending':
        qs = qs.filter(
            Q(payment_status=JobCard.PaymentStatus.PENDING)
            | Q(payment_status=JobCard.PaymentStatus.UNPAID)
        )

    master_city = params.get('master_city') or params.get('service_city')
    if master_city:
        qs = qs.filter(master_city_id=master_city)

    created_by = params.get('created_by')
    if created_by:
        qs = qs.filter(created_by_id=created_by)

    date_from = params.get('date_from') or params.get('booking_date_from')
    date_to = params.get('date_to') or params.get('booking_date_to')
    if date_from:
        qs = qs.filter(schedule_datetime__date__gte=date_from)
    if date_to:
        qs = qs.filter(schedule_datetime__date__lte=date_to)

    search = params.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(code__icontains=search)
            | Q(client__full_name__icontains=search)
            | Q(client__mobile__icontains=search)
        )

    return qs


class PendingPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and manage bookings with outstanding balances.
    """
    serializer_class = JobCardSerializer
    permission_classes = [IsCRMOperationalUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'client__full_name', 'client__mobile']
    ordering_fields = ['created_at', 'schedule_datetime', 'pending_amount', 'paid_amount', 'total_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        return billable_outstanding_queryset(self.request)

    @extend_schema(summary='Pending payment dashboard stats')
    @decorators.action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        filtered_qs = billable_outstanding_queryset(request)
        aggregates = filtered_qs.aggregate(
            total_outstanding=Sum('pending_amount'),
            paid_on_outstanding=Sum('paid_amount'),
        )
        today = timezone.localdate()
        start = timezone.make_aware(datetime.combine(today, time.min))
        end = timezone.make_aware(datetime.combine(today, time.max))
        todays_collections = (
            BookingPayment.objects.filter(created_at__range=(start, end))
            .aggregate(total=Sum('amount'))
            .get('total')
        )
        lifetime_collected = (
            BookingPayment.objects.aggregate(total=Sum('amount')).get('total')
        )

        return Response({
            'total_outstanding_amount': aggregates['total_outstanding'] or 0,
            # Paid portion on currently outstanding bookings (filtered).
            'total_collected_amount': aggregates['paid_on_outstanding'] or 0,
            'lifetime_collected_amount': lifetime_collected or 0,
            'total_pending_bookings': filtered_qs.count(),
            'todays_collections': todays_collections or 0,
        })

    @extend_schema(
        summary='Collect remaining payment on a booking',
        request=CollectPaymentSerializer,
    )
    @decorators.action(detail=True, methods=['post'], url_path='collect')
    def collect(self, request, pk=None):
        jobcard = self.get_object()
        serializer = CollectPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            JobCardService.collect_pending_payment(
                jobcard,
                user=request.user,
                amount=data['amount'],
                payment_mode=data['payment_mode'],
                remarks=data.get('remarks', ''),
            )
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        jobcard.refresh_from_db()
        if request.user and request.user.is_authenticated:
            ActivityLog.objects.create(
                user=request.user,
                action='Collected Payment',
                booking_id=jobcard.code,
                details=(
                    f"₹{data['amount']} via {data['payment_mode']}. "
                    f"Balance: ₹{jobcard.pending_amount}"
                ),
            )
        return Response(JobCardSerializer(jobcard, context={'request': request}).data)

    @extend_schema(summary='Payment history for a booking')
    @decorators.action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        jobcard = self.get_object()
        records = jobcard.payment_records.select_related('collected_by').order_by('-created_at')
        return Response(BookingPaymentSerializer(records, many=True).data)
