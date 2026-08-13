from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import (
    AccountsAlert,
    BookingCostSnapshot,
    Branch,
    BranchCityMap,
    Chemical,
    ChemicalUsage,
    DailyBranchPnL,
    Equipment,
    ExpenseCategory,
    ExpenseEntry,
    MonthlyBranchPnL,
    MonthlyOverheadRate,
    StockBalance,
    StockLot,
    StockMovement,
    Supplier,
)
from accounts.permissions import AccountsAccess
from accounts.serializers import (
    AccountsAlertSerializer,
    AdjustSerializer,
    BookingCostSnapshotSerializer,
    BranchCityMapSerializer,
    BranchSerializer,
    ChemicalSerializer,
    ChemicalUsageCreateSerializer,
    ChemicalUsageSerializer,
    DailyBranchPnLSerializer,
    EquipmentSerializer,
    ExpenseCategorySerializer,
    ExpenseEntrySerializer,
    IssueSerializer,
    MonthlyBranchPnLSerializer,
    MonthlyOverheadRateSerializer,
    PurchaseSerializer,
    StockBalanceSerializer,
    StockLotSerializer,
    StockMovementSerializer,
    SupplierSerializer,
    TransferSerializer,
)
from accounts.services import (
    adjust_stock,
    allocate_monthly_overhead,
    issue_stock,
    purchase_return,
    purchase_stock,
    rebuild_daily_pnl,
    rebuild_monthly_pnl,
    record_chemical_usage,
    return_stock,
    run_accounts_alerts,
    transfer_stock,
)
from accounts.services.profit import recalculate_booking_cost
from core.models import JobCard, Technician


class AccountsPagination(PageNumberPagination):
    """CRM accounts masters/tables — allow page_size up to 200."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class AccountsModelViewSet(viewsets.ModelViewSet):
    permission_classes = [AccountsAccess]
    pagination_class = AccountsPagination


class BranchViewSet(AccountsModelViewSet):
    queryset = Branch.objects.select_related('city').all()
    serializer_class = BranchSerializer
    filterset_fields = ['is_active', 'city']
    search_fields = ['name', 'code']


class BranchCityMapViewSet(AccountsModelViewSet):
    queryset = BranchCityMap.objects.select_related('branch', 'city').all()
    serializer_class = BranchCityMapSerializer


class SupplierViewSet(AccountsModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'mobile', 'gstin']


class ChemicalViewSet(AccountsModelViewSet):
    queryset = Chemical.objects.all()
    serializer_class = ChemicalSerializer
    filterset_fields = ['is_active', 'unit']
    search_fields = ['name', 'sku']


class EquipmentViewSet(AccountsModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'sku']


class StockBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AccountsAccess]
    pagination_class = AccountsPagination
    queryset = StockBalance.objects.select_related('branch', 'chemical', 'equipment').all()
    serializer_class = StockBalanceSerializer
    filterset_fields = ['branch', 'item_type', 'chemical', 'equipment']

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        rows = []
        for bal in self.get_queryset():
            ser = self.get_serializer(bal)
            if ser.data.get('is_low'):
                rows.append(ser.data)
        return Response(rows)


class StockLotViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AccountsAccess]
    pagination_class = AccountsPagination
    queryset = StockLot.objects.select_related('branch', 'chemical', 'equipment', 'supplier').all()
    serializer_class = StockLotSerializer
    filterset_fields = ['branch', 'item_type', 'chemical', 'equipment']

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        days = int(request.query_params.get('days', 30))
        today = timezone.localdate()
        qs = self.get_queryset().filter(
            qty_remaining__gt=0,
            expiry_date__isnull=False,
            expiry_date__lte=today + timedelta(days=days),
        )
        return Response(self.get_serializer(qs, many=True).data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AccountsAccess]
    pagination_class = AccountsPagination
    queryset = StockMovement.objects.select_related(
        'branch', 'chemical', 'supplier', 'technician',
    ).all()
    serializer_class = StockMovementSerializer
    filterset_fields = ['branch', 'movement_type', 'chemical', 'jobcard', 'payment_pending']

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('from')
        date_to = self.request.query_params.get('to')
        if date_from:
            qs = qs.filter(movement_date__gte=date_from)
        if date_to:
            qs = qs.filter(movement_date__lte=date_to)
        return qs

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        ser = PurchaseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        mv = purchase_stock(
            branch=Branch.objects.get(pk=d['branch_id']),
            item_type=d['item_type'],
            chemical=Chemical.objects.filter(pk=d.get('chemical_id')).first(),
            equipment=Equipment.objects.filter(pk=d.get('equipment_id')).first(),
            supplier=Supplier.objects.filter(pk=d.get('supplier_id')).first(),
            quantity=d['quantity'],
            unit_cost=d['unit_cost'],
            batch_no=d.get('batch_no') or '',
            expiry_date=d.get('expiry_date'),
            movement_date=d.get('movement_date'),
            reference=d.get('reference') or '',
            remarks=d.get('remarks') or '',
            payment_pending=d.get('payment_pending') or False,
            user=request.user,
        )
        return Response(StockMovementSerializer(mv).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def adjust(self, request):
        ser = AdjustSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        mv = adjust_stock(
            branch=Branch.objects.get(pk=d['branch_id']),
            item_type=d['item_type'],
            chemical=Chemical.objects.filter(pk=d.get('chemical_id')).first(),
            equipment=Equipment.objects.filter(pk=d.get('equipment_id')).first(),
            quantity_delta=d['quantity_delta'],
            unit_cost=d.get('unit_cost') or 0,
            remarks=d.get('remarks') or '',
            user=request.user,
        )
        return Response(StockMovementSerializer(mv).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def issue(self, request):
        ser = IssueSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        mvs = issue_stock(
            branch=Branch.objects.get(pk=d['branch_id']),
            chemical=Chemical.objects.get(pk=d['chemical_id']),
            quantity=d['quantity'],
            technician=Technician.objects.filter(pk=d.get('technician_id')).first(),
            jobcard=JobCard.objects.filter(pk=d.get('jobcard_id')).first(),
            remarks=d.get('remarks') or '',
            user=request.user,
        )
        return Response(StockMovementSerializer(mvs, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def purchase_return(self, request):
        d = request.data
        mv = purchase_return(
            branch=Branch.objects.get(pk=d.get('branch_id')),
            item_type=d.get('item_type') or 'chemical',
            chemical=Chemical.objects.filter(pk=d.get('chemical_id')).first(),
            equipment=Equipment.objects.filter(pk=d.get('equipment_id')).first(),
            lot=StockLot.objects.filter(pk=d.get('lot_id')).first(),
            supplier=Supplier.objects.filter(pk=d.get('supplier_id')).first(),
            quantity=d.get('quantity'),
            remarks=d.get('remarks') or '',
            user=request.user,
        )
        return Response(StockMovementSerializer(mv).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='stock-return')
    def stock_return(self, request):
        d = request.data
        mv = return_stock(
            branch=Branch.objects.get(pk=d.get('branch_id')),
            chemical=Chemical.objects.get(pk=d.get('chemical_id')),
            quantity=d.get('quantity'),
            technician=Technician.objects.filter(pk=d.get('technician_id')).first(),
            unit_cost=d.get('unit_cost') or 0,
            remarks=d.get('remarks') or '',
            user=request.user,
        )
        return Response(StockMovementSerializer(mv).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        ser = TransferSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        out_mv, in_mv = transfer_stock(
            from_branch=Branch.objects.get(pk=d['from_branch_id']),
            to_branch=Branch.objects.get(pk=d['to_branch_id']),
            item_type=d['item_type'],
            chemical=Chemical.objects.filter(pk=d.get('chemical_id')).first(),
            equipment=Equipment.objects.filter(pk=d.get('equipment_id')).first(),
            quantity=d['quantity'],
            remarks=d.get('remarks') or '',
            user=request.user,
        )
        return Response(
            {
                'out': StockMovementSerializer(out_mv).data,
                'in': StockMovementSerializer(in_mv).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        mv = self.get_object()
        mv.payment_pending = False
        mv.save(update_fields=['payment_pending', 'updated_at'])
        return Response(StockMovementSerializer(mv).data)


class ChemicalUsageViewSet(AccountsModelViewSet):
    queryset = ChemicalUsage.objects.select_related('chemical', 'branch', 'jobcard').all()
    serializer_class = ChemicalUsageSerializer
    filterset_fields = ['jobcard', 'chemical', 'branch', 'source']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def create(self, request, *args, **kwargs):
        ser = ChemicalUsageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        usage = record_chemical_usage(
            job=JobCard.objects.get(pk=d['jobcard_id']),
            chemical=Chemical.objects.get(pk=d['chemical_id']),
            quantity_ml=d['quantity_ml'],
            source=d.get('source') or 'crm',
            remarks=d.get('remarks') or '',
            deduct_stock=d.get('deduct_stock', True),
            user=request.user,
        )
        return Response(ChemicalUsageSerializer(usage).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        job = instance.jobcard
        instance.delete()
        if job and job.status == JobCard.JobStatus.DONE:
            recalculate_booking_cost(job)


class ExpenseCategoryViewSet(AccountsModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    filterset_fields = ['group', 'is_active', 'is_overhead']


class ExpenseEntryViewSet(AccountsModelViewSet):
    queryset = ExpenseEntry.objects.select_related('branch', 'category', 'technician').all()
    serializer_class = ExpenseEntrySerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ['branch', 'category', 'status', 'technician', 'jobcard', 'payment_mode']

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('from')
        date_to = self.request.query_params.get('to')
        group = self.request.query_params.get('group')
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)
        if group:
            qs = qs.filter(category__group=group)
        return qs

    def perform_create(self, serializer):
        entry = serializer.save(created_by=self.request.user)
        if entry.jobcard_id and entry.status == ExpenseEntry.Status.POSTED:
            recalculate_booking_cost(entry.jobcard_id)

    def perform_update(self, serializer):
        entry = serializer.save()
        if entry.jobcard_id:
            recalculate_booking_cost(entry.jobcard_id)


class BookingCostSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = AccountsPagination
    permission_classes = [AccountsAccess]
    queryset = BookingCostSnapshot.objects.select_related('branch', 'jobcard').all()
    serializer_class = BookingCostSnapshotSerializer
    filterset_fields = ['branch', 'jobcard']

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('from')
        date_to = self.request.query_params.get('to')
        if date_from:
            qs = qs.filter(booking_date__gte=date_from)
        if date_to:
            qs = qs.filter(booking_date__lte=date_to)
        return qs

    @action(detail=False, methods=['post'])
    def recalculate(self, request):
        job_id = request.data.get('jobcard_id')
        if not job_id:
            return Response({'detail': 'jobcard_id required'}, status=400)
        snap = recalculate_booking_cost(int(job_id))
        if not snap:
            return Response({'detail': 'Job not found'}, status=404)
        return Response(BookingCostSnapshotSerializer(snap).data)


class DailyPnLViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AccountsAccess]
    pagination_class = AccountsPagination
    queryset = DailyBranchPnL.objects.select_related('branch').all()
    serializer_class = DailyBranchPnLSerializer
    filterset_fields = ['branch', 'date']


class MonthlyPnLViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AccountsAccess]
    pagination_class = AccountsPagination
    queryset = MonthlyBranchPnL.objects.select_related('branch').all()
    serializer_class = MonthlyBranchPnLSerializer
    filterset_fields = ['branch', 'year', 'month']


class OverheadViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AccountsAccess]
    pagination_class = AccountsPagination
    queryset = MonthlyOverheadRate.objects.select_related('branch').all()
    serializer_class = MonthlyOverheadRateSerializer
    filterset_fields = ['branch', 'year', 'month']

    @action(detail=False, methods=['post'])
    def allocate(self, request):
        year = request.data.get('year')
        month = request.data.get('month')
        branch_id = request.data.get('branch_id')
        branch = Branch.objects.filter(pk=branch_id).first() if branch_id else None
        rows = allocate_monthly_overhead(
            year=int(year) if year else None,
            month=int(month) if month else None,
            branch=branch,
        )
        return Response(MonthlyOverheadRateSerializer(rows, many=True).data)


class AccountsAlertViewSet(AccountsModelViewSet):
    queryset = AccountsAlert.objects.select_related('branch').all()
    serializer_class = AccountsAlertSerializer
    filterset_fields = ['alert_type', 'severity', 'branch', 'is_read', 'is_resolved']
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    @action(detail=False, methods=['post'])
    def run(self, request):
        stats = run_accounts_alerts()
        return Response(stats)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.is_resolved = True
        alert.is_read = True
        alert.save(update_fields=['is_resolved', 'is_read', 'updated_at'])
        return Response(AccountsAlertSerializer(alert).data)


class AccountsDashboardView(APIView):
    permission_classes = [AccountsAccess]

    def get(self, request):
        today = timezone.localdate()
        branch_id = request.query_params.get('branch')
        daily = DailyBranchPnL.objects.filter(date=today)
        monthly = MonthlyBranchPnL.objects.filter(year=today.year, month=today.month)
        if branch_id:
            daily = daily.filter(branch_id=branch_id)
            monthly = monthly.filter(branch_id=branch_id)

        def sum_field(qs, field):
            return qs.aggregate(v=Sum(field))['v'] or 0

        low_stock = 0
        for bal in StockBalance.objects.select_related('chemical').filter(chemical__isnull=False):
            if bal.quantity <= (bal.chemical.reorder_level or 0):
                low_stock += 1

        unread_alerts = AccountsAlert.objects.filter(is_resolved=False, is_read=False).count()

        return Response({
            'date': today.isoformat(),
            'daily': {
                'sales': sum_field(daily, 'sales'),
                'expenses': sum_field(daily, 'office_expenses') + sum_field(daily, 'direct_expenses'),
                'gross_profit': sum_field(daily, 'gross_profit'),
                'company_net_profit': sum_field(daily, 'company_net_profit'),
                'chemical_cogs': sum_field(daily, 'chemical_cogs'),
                'booking_count': sum_field(daily, 'booking_count'),
                'avg_cost_per_booking': sum_field(daily, 'avg_cost_per_booking'),
            },
            'monthly': {
                'sales': sum_field(monthly, 'sales'),
                'expenses': sum_field(monthly, 'office_expenses') + sum_field(monthly, 'direct_expenses'),
                'gross_profit': sum_field(monthly, 'gross_profit'),
                'company_net_profit': sum_field(monthly, 'company_net_profit'),
                'inventory_value': sum_field(monthly, 'inventory_value'),
                'chemical_consumption': sum_field(monthly, 'chemical_consumption'),
                'booking_count': sum_field(monthly, 'booking_count'),
                'avg_cost_per_booking': sum_field(monthly, 'avg_cost_per_booking'),
                'avg_profit_per_booking': sum_field(monthly, 'avg_profit_per_booking'),
            },
            'low_stock_count': low_stock,
            'unread_alerts': unread_alerts,
        })


class AccountsRebuildView(APIView):
    permission_classes = [AccountsAccess]

    def post(self, request):
        day = request.data.get('date')
        year = request.data.get('year')
        month = request.data.get('month')
        if day:
            d = datetime.strptime(day, '%Y-%m-%d').date()
            rebuild_daily_pnl(day=d)
        else:
            rebuild_daily_pnl()
        rebuild_monthly_pnl(
            year=int(year) if year else None,
            month=int(month) if month else None,
        )
        return Response({'ok': True})


class AccountsExportView(APIView):
    """CSV exports for inventory, expenses, booking profit, P&L."""

    permission_classes = [AccountsAccess]

    def get(self, request):
        report = request.query_params.get('report', 'booking_profit')
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        if report == 'inventory':
            writer.writerow(['Branch', 'Item', 'Quantity', 'Reorder', 'Low'])
            for bal in StockBalance.objects.select_related('branch', 'chemical', 'equipment'):
                name = bal.chemical.name if bal.chemical_id else (bal.equipment.name if bal.equipment_id else '')
                reorder = bal.chemical.reorder_level if bal.chemical_id else (bal.equipment.reorder_level if bal.equipment_id else 0)
                writer.writerow([bal.branch.name, name, bal.quantity, reorder, bal.quantity <= reorder])
        elif report == 'movements':
            writer.writerow(['Date', 'Type', 'Branch', 'Item', 'Qty', 'Unit Cost', 'Line Cost', 'Ref'])
            for mv in StockMovement.objects.select_related('branch', 'chemical')[:5000]:
                writer.writerow([
                    mv.movement_date, mv.movement_type, mv.branch.name,
                    mv.chemical.name if mv.chemical_id else '',
                    mv.quantity, mv.unit_cost, mv.line_cost, mv.reference,
                ])
        elif report == 'expenses':
            writer.writerow(['Date', 'Branch', 'Group', 'Category', 'Amount', 'GST', 'Vendor', 'Job'])
            for e in ExpenseEntry.objects.select_related('branch', 'category')[:5000]:
                writer.writerow([
                    e.entry_date, e.branch.name, e.category.group, e.category.name,
                    e.amount, e.gst_amount, e.vendor_name, e.jobcard_id or '',
                ])
        elif report == 'monthly_pnl':
            writer.writerow([
                'Branch', 'Year', 'Month', 'Sales', 'COGS', 'Expenses', 'Tech Cost',
                'Overhead', 'Gross Profit', 'Company Net', 'Bookings',
            ])
            for row in MonthlyBranchPnL.objects.select_related('branch'):
                writer.writerow([
                    row.branch.name, row.year, row.month, row.sales, row.chemical_cogs,
                    row.office_expenses + row.direct_expenses, row.technician_cost,
                    row.overhead, row.gross_profit, row.company_net_profit, row.booking_count,
                ])
        else:
            writer.writerow([
                'Booking Date', 'Job', 'Branch', 'Visit Revenue', 'Chemical', 'Expenses',
                'Tech Cost', 'Overhead', 'Total Cost', 'Gross Profit', 'Company Net',
            ])
            qs = BookingCostSnapshot.objects.select_related('branch')
            date_from = request.query_params.get('from')
            date_to = request.query_params.get('to')
            if date_from:
                qs = qs.filter(booking_date__gte=date_from)
            if date_to:
                qs = qs.filter(booking_date__lte=date_to)
            for s in qs[:10000]:
                writer.writerow([
                    s.booking_date, s.jobcard_id,
                    s.branch.name if s.branch_id else '',
                    s.visit_revenue, s.chemical_cost, s.direct_expense_cost,
                    s.technician_cost, s.overhead_cost, s.total_cost,
                    s.gross_profit, s.company_net_profit,
                ])

        resp = HttpResponse(buffer.getvalue(), content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="accounts-{report}.csv"'
        return resp
