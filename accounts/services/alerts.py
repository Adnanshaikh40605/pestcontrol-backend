"""Generate CRM accounts alerts (low stock, expiry, payments, expenses, digests)."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from accounts.models import (
    AccountsAlert,
    BookingCostSnapshot,
    Branch,
    Chemical,
    DailyBranchPnL,
    ExpenseEntry,
    MonthlyBranchPnL,
    StockBalance,
    StockLot,
    StockMovement,
)


def _upsert_alert(
    *,
    alert_type: str,
    title: str,
    message: str,
    severity: str = AccountsAlert.Severity.WARNING,
    branch: Branch | None = None,
    payload: dict | None = None,
) -> AccountsAlert:
    open_alert = AccountsAlert.objects.filter(
        alert_type=alert_type,
        branch=branch,
        title=title,
        is_resolved=False,
    ).first()
    if open_alert:
        open_alert.message = message
        open_alert.severity = severity
        open_alert.payload = payload or {}
        open_alert.save(update_fields=['message', 'severity', 'payload', 'updated_at'])
        return open_alert
    return AccountsAlert.objects.create(
        alert_type=alert_type,
        severity=severity,
        branch=branch,
        title=title,
        message=message,
        payload=payload or {},
    )


def run_accounts_alerts(*, expiry_days: int = 30, high_expense_threshold: Decimal = Decimal('10000')) -> dict:
    created = {'low_stock': 0, 'expiry': 0, 'supplier': 0, 'high_expense': 0, 'digests': 0}
    today = timezone.localdate()

    # Low stock
    for bal in StockBalance.objects.select_related('chemical', 'equipment', 'branch').filter(
        item_type=StockBalance.ItemType.CHEMICAL,
        chemical__isnull=False,
    ):
        reorder = bal.chemical.reorder_level if bal.chemical else Decimal('0')
        if bal.quantity <= reorder:
            _upsert_alert(
                alert_type=AccountsAlert.AlertType.LOW_STOCK,
                branch=bal.branch,
                title=f'Low stock: {bal.chemical.name}',
                message=f'{bal.branch.name}: {bal.chemical.name} qty {bal.quantity} ≤ reorder {reorder}.',
                severity=AccountsAlert.Severity.WARNING,
                payload={'chemical_id': bal.chemical_id, 'quantity': str(bal.quantity)},
            )
            created['low_stock'] += 1

    # Expiry
    limit = today + timedelta(days=expiry_days)
    for lot in StockLot.objects.filter(
        qty_remaining__gt=0,
        expiry_date__isnull=False,
        expiry_date__lte=limit,
    ).select_related('chemical', 'branch'):
        _upsert_alert(
            alert_type=AccountsAlert.AlertType.EXPIRY,
            branch=lot.branch,
            title=f'Expiring: {lot.chemical.name if lot.chemical else "Item"}',
            message=f'Lot #{lot.id} expires {lot.expiry_date} (qty {lot.qty_remaining}).',
            severity=(
                AccountsAlert.Severity.CRITICAL
                if lot.expiry_date <= today
                else AccountsAlert.Severity.WARNING
            ),
            payload={'lot_id': lot.id, 'expiry_date': str(lot.expiry_date)},
        )
        created['expiry'] += 1

    # Pending supplier payments
    for mv in StockMovement.objects.filter(
        movement_type=StockMovement.MovementType.PURCHASE,
        payment_pending=True,
    ).select_related('branch', 'supplier')[:200]:
        _upsert_alert(
            alert_type=AccountsAlert.AlertType.SUPPLIER_PAYMENT,
            branch=mv.branch,
            title=f'Unpaid purchase #{mv.id}',
            message=f'{mv.supplier or "Supplier"} — ₹{mv.line_cost} pending ({mv.movement_date}).',
            payload={'movement_id': mv.id},
        )
        created['supplier'] += 1

    # High expense (today)
    for br in Branch.objects.filter(is_active=True):
        day_total = (
            ExpenseEntry.objects.filter(
                branch=br,
                status=ExpenseEntry.Status.POSTED,
                entry_date=today,
            ).aggregate(total=Sum('amount'))['total']
            or 0
        )
        if Decimal(str(day_total)) >= high_expense_threshold:
            _upsert_alert(
                alert_type=AccountsAlert.AlertType.HIGH_EXPENSE,
                branch=br,
                title=f'High expenses today — {br.name}',
                message=f'Total posted expenses ₹{day_total} ≥ threshold ₹{high_expense_threshold}.',
                severity=AccountsAlert.Severity.WARNING,
                payload={'amount': str(day_total)},
            )
            created['high_expense'] += 1

    # Daily profit digest
    for pnl in DailyBranchPnL.objects.filter(date=today).select_related('branch'):
        _upsert_alert(
            alert_type=AccountsAlert.AlertType.DAILY_PROFIT,
            branch=pnl.branch,
            title=f'Daily P&L — {pnl.branch.name} {today}',
            message=(
                f'Sales ₹{pnl.sales} · Gross ₹{pnl.gross_profit} · '
                f'Company net ₹{pnl.company_net_profit} · Bookings {pnl.booking_count}'
            ),
            severity=AccountsAlert.Severity.INFO,
            payload={'daily_pnl_id': pnl.id},
        )
        created['digests'] += 1

    # Monthly digest on first day of next month-ish — always refresh current month
    for pnl in MonthlyBranchPnL.objects.filter(year=today.year, month=today.month).select_related('branch'):
        _upsert_alert(
            alert_type=AccountsAlert.AlertType.MONTHLY_PROFIT,
            branch=pnl.branch,
            title=f'Monthly P&L — {pnl.branch.name} {pnl.year}-{pnl.month:02d}',
            message=(
                f'Sales ₹{pnl.sales} · Gross ₹{pnl.gross_profit} · '
                f'Company net ₹{pnl.company_net_profit} · Avg profit/booking ₹{pnl.avg_profit_per_booking}'
            ),
            severity=AccountsAlert.Severity.INFO,
            payload={'monthly_pnl_id': pnl.id},
        )
        created['digests'] += 1

    # Excess chemical: usage line cost > 25% of visit revenue on a booking
    for snap in BookingCostSnapshot.objects.filter(booking_date=today).select_related('branch', 'jobcard'):
        base = snap.visit_revenue or snap.booking_amount
        if base and snap.chemical_cost > (base * Decimal('0.25')):
            _upsert_alert(
                alert_type=AccountsAlert.AlertType.EXCESS_CHEMICAL,
                branch=snap.branch,
                title=f'High chemical cost — Job #{snap.jobcard_id}',
                message=f'Chemical ₹{snap.chemical_cost} is over 25% of visit revenue ₹{base}.',
                severity=AccountsAlert.Severity.WARNING,
                payload={'job_id': snap.jobcard_id},
            )

    return created
