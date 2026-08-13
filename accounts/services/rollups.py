"""Daily / monthly branch P&L rollups from snapshots + expenses."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from accounts.models import (
    BookingCostSnapshot,
    Branch,
    DailyBranchPnL,
    ExpenseCategory,
    ExpenseEntry,
    MonthlyBranchPnL,
    StockLot,
)
from core.payout_engine import quantize_money


def _inventory_value(branch: Branch) -> Decimal:
    total = (
        StockLot.objects.filter(branch=branch, qty_remaining__gt=0)
        .aggregate(v=Sum('qty_remaining'))  # placeholder; compute properly below
    )
    # Sum qty_remaining * unit_cost
    value = Decimal('0')
    for lot in StockLot.objects.filter(branch=branch, qty_remaining__gt=0).only(
        'qty_remaining', 'unit_cost',
    ):
        value += Decimal(lot.qty_remaining) * Decimal(lot.unit_cost)
    return quantize_money(value)


def rebuild_daily_pnl(*, day: date | None = None, branch: Branch | None = None) -> list[DailyBranchPnL]:
    day = day or timezone.localdate()
    branches = [branch] if branch else list(Branch.objects.filter(is_active=True))
    rows: list[DailyBranchPnL] = []

    for br in branches:
        snaps = BookingCostSnapshot.objects.filter(branch=br, booking_date=day)
        agg = snaps.aggregate(
            sales=Sum('visit_revenue'),
            cogs=Sum('chemical_cost'),
            direct=Sum('direct_expense_cost'),
            tech=Sum('technician_cost'),
            overhead=Sum('overhead_cost'),
            gp=Sum('gross_profit'),
            cnp=Sum('company_net_profit'),
            total_cost=Sum('total_cost'),
        )
        count = snaps.count()
        office = (
            ExpenseEntry.objects.filter(
                branch=br,
                status=ExpenseEntry.Status.POSTED,
                entry_date=day,
                category__group__in=[
                    ExpenseCategory.Group.OFFICE,
                    ExpenseCategory.Group.MARKETING,
                ],
            ).aggregate(total=Sum('amount'))['total']
            or 0
        )
        sales = quantize_money(agg['sales'] or 0)
        total_cost = quantize_money(agg['total_cost'] or 0)
        gp = quantize_money(agg['gp'] or 0)
        row, _ = DailyBranchPnL.objects.update_or_create(
            branch=br,
            date=day,
            defaults={
                'sales': sales,
                'chemical_cogs': quantize_money(agg['cogs'] or 0),
                'direct_expenses': quantize_money(agg['direct'] or 0),
                'technician_cost': quantize_money(agg['tech'] or 0),
                'overhead': quantize_money(agg['overhead'] or 0),
                'office_expenses': quantize_money(office),
                'gross_profit': gp,
                'company_net_profit': quantize_money(agg['cnp'] or 0),
                'booking_count': count,
                'avg_cost_per_booking': (
                    quantize_money(total_cost / count) if count else Decimal('0.00')
                ),
                'avg_profit_per_booking': (
                    quantize_money(gp / count) if count else Decimal('0.00')
                ),
                'inventory_value': _inventory_value(br),
            },
        )
        rows.append(row)
    return rows


def rebuild_monthly_pnl(
    *,
    year: int | None = None,
    month: int | None = None,
    branch: Branch | None = None,
) -> list[MonthlyBranchPnL]:
    today = timezone.localdate()
    year = year or today.year
    month = month or today.month
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    branches = [branch] if branch else list(Branch.objects.filter(is_active=True))
    rows: list[MonthlyBranchPnL] = []

    for br in branches:
        snaps = BookingCostSnapshot.objects.filter(
            branch=br, booking_date__gte=start, booking_date__lte=end,
        )
        agg = snaps.aggregate(
            sales=Sum('visit_revenue'),
            cogs=Sum('chemical_cost'),
            direct=Sum('direct_expense_cost'),
            tech=Sum('technician_cost'),
            overhead=Sum('overhead_cost'),
            gp=Sum('gross_profit'),
            cnp=Sum('company_net_profit'),
            total_cost=Sum('total_cost'),
        )
        count = snaps.count()
        office = (
            ExpenseEntry.objects.filter(
                branch=br,
                status=ExpenseEntry.Status.POSTED,
                entry_date__gte=start,
                entry_date__lte=end,
                category__group__in=[
                    ExpenseCategory.Group.OFFICE,
                    ExpenseCategory.Group.MARKETING,
                ],
            ).aggregate(total=Sum('amount'))['total']
            or 0
        )
        from accounts.models import ChemicalUsage

        consumption = (
            ChemicalUsage.objects.filter(
                branch=br,
                created_at__date__gte=start,
                created_at__date__lte=end,
            ).aggregate(total=Sum('quantity_ml'))['total']
            or 0
        )
        sales = quantize_money(agg['sales'] or 0)
        total_cost = quantize_money(agg['total_cost'] or 0)
        gp = quantize_money(agg['gp'] or 0)
        row, _ = MonthlyBranchPnL.objects.update_or_create(
            branch=br,
            year=year,
            month=month,
            defaults={
                'sales': sales,
                'chemical_cogs': quantize_money(agg['cogs'] or 0),
                'direct_expenses': quantize_money(agg['direct'] or 0),
                'technician_cost': quantize_money(agg['tech'] or 0),
                'overhead': quantize_money(agg['overhead'] or 0),
                'office_expenses': quantize_money(office),
                'gross_profit': gp,
                'company_net_profit': quantize_money(agg['cnp'] or 0),
                'booking_count': count,
                'avg_cost_per_booking': (
                    quantize_money(total_cost / count) if count else Decimal('0.00')
                ),
                'avg_profit_per_booking': (
                    quantize_money(gp / count) if count else Decimal('0.00')
                ),
                'inventory_value': _inventory_value(br),
                'chemical_consumption': Decimal(str(consumption)),
            },
        )
        rows.append(row)
    return rows


def rebuild_range(days: int = 31) -> None:
    today = timezone.localdate()
    for i in range(days):
        rebuild_daily_pnl(day=today - timedelta(days=i))
    rebuild_monthly_pnl(year=today.year, month=today.month)
