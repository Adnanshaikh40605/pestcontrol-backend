"""CRM APIs for technician settlements and revenue reports."""
from __future__ import annotations

from datetime import datetime

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import JobCard, TechnicianSettlement
from core.permissions import IsCRMOperationalUser
from core.payout_engine import is_revenue_model_enabled
from core.settlement_engine import (
    SettlementError,
    approve_settlement,
    build_settlements_for_period,
    cancel_settlement,
    mark_settlement_paid,
)
from core.settlement_excel import revenue_sharing_workbook, settlements_workbook
from core.settlement_serializers import (
    SettlementBuildSerializer,
    TechnicianSettlementSerializer,
)


class TechnicianSettlementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCRMOperationalUser]
    serializer_class = TechnicianSettlementSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = TechnicianSettlement.objects.select_related(
            'technician', 'partner', 'approved_by', 'paid_by',
        ).prefetch_related('line_items__job', 'line_items__participation__technician')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        tech = self.request.query_params.get('technician')
        if tech:
            qs = qs.filter(technician_id=tech)
        period_start = self.request.query_params.get('period_start')
        period_end = self.request.query_params.get('period_end')
        if period_start:
            qs = qs.filter(period_end__gte=period_start)
        if period_end:
            qs = qs.filter(period_start__lte=period_end)
        return qs.order_by('-period_end', '-id')

    def create(self, request, *args, **kwargs):
        """POST /settlements/ builds draft/pending settlements for a period."""
        if not is_revenue_model_enabled():
            return Response(
                {'error': 'REVENUE_MODEL_V2 is disabled'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = SettlementBuildSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            created = build_settlements_for_period(
                period_start=data['period_start'],
                period_end=data['period_end'],
                cadence=data.get('cadence') or TechnicianSettlement.Cadence.WEEKLY,
                technician_ids=data.get('technician_ids') or None,
                created_by=request.user,
            )
        except SettlementError as exc:
            return Response(
                {'error': exc.message, 'code': exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        out = TechnicianSettlementSerializer(created, many=True).data
        return Response(
            {'count': len(created), 'results': out},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        if not is_revenue_model_enabled():
            return Response({'error': 'REVENUE_MODEL_V2 is disabled'}, status=400)
        settlement = self.get_object()
        try:
            settlement = approve_settlement(settlement, user=request.user)
        except SettlementError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response(TechnicianSettlementSerializer(settlement).data)

    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        if not is_revenue_model_enabled():
            return Response({'error': 'REVENUE_MODEL_V2 is disabled'}, status=400)
        settlement = self.get_object()
        try:
            settlement = mark_settlement_paid(settlement, user=request.user)
        except SettlementError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response(TechnicianSettlementSerializer(settlement).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        if not is_revenue_model_enabled():
            return Response({'error': 'REVENUE_MODEL_V2 is disabled'}, status=400)
        settlement = self.get_object()
        try:
            settlement = cancel_settlement(settlement)
        except SettlementError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=400)
        return Response(TechnicianSettlementSerializer(settlement).data)

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        """Excel export of settlements (optional ?ids=1,2,3 or date filters)."""
        qs = self.get_queryset()
        ids = request.query_params.get('ids')
        if ids:
            id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]
            qs = qs.filter(id__in=id_list)
        settlements = list(qs[:500])
        buf = settlements_workbook(settlements)
        filename = f'settlements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'], url_path='revenue-sharing-report')
    def revenue_sharing_report(self, request):
        """Excel of revenue-sharing jobs/earnings in a date window."""
        from partner.models import PartnerEarning

        date_from = parse_date(request.query_params.get('from') or '')
        date_to = parse_date(request.query_params.get('to') or '')
        earnings = PartnerEarning.objects.select_related(
            'partner', 'job', 'partner__core_technician',
        ).exclude(job__payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT)
        if date_from:
            earnings = earnings.filter(created_at__date__gte=date_from)
        if date_to:
            earnings = earnings.filter(created_at__date__lte=date_to)
        rows = []
        for e in earnings.order_by('-created_at')[:2000]:
            job = e.job
            tech = getattr(e.partner, 'core_technician', None)
            rows.append({
                'job_code': job.code,
                'completed_at': job.completed_at.isoformat() if job.completed_at else '',
                'technician': tech.name if tech else '',
                'partner': e.partner.full_name,
                'payment_model': job.payment_model or '',
                'payout_status': job.payout_status or '',
                'visit_revenue': float(job.visit_revenue_amount or 0),
                'tech_pool': float(job.technician_pool_amount or 0),
                'company_share': float(job.company_share_amount or 0),
                'visit_payout': float(job.visit_payout_amount or 0),
                'earning_amount': float(e.amount or 0),
                'earning_approved': bool(e.is_approved),
            })
        buf = revenue_sharing_workbook(rows)
        filename = f'revenue_sharing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
