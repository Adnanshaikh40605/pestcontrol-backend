# Accounts Management — Spec & Implementation Status

Source requirements for PestControl99 inventory, expenses, booking profit, dashboards, reports, and alerts.

## Decisions

- **Profit views (both):** Gross booking profit + Company net profit on every completed booking.
- **Chemical usage:** Partner app and CRM can enter usage; cost from purchase FIFO ₹/unit.
- **Revenue Model v2 unchanged:** Accounts sits beside 40/60 payouts and settlements.

## Modules

### 1. Inventory & Stock
Chemical / Equipment / Supplier masters · Purchase · Purchase return · Adjustment · Issue · Return · Branch transfer · Low stock · Expiry · Movement history.

### 2. Expense Management
Office, Marketing, Technician, Purchase categories with date, branch, vendor, technician, booking, amount, GST, payment mode, bill, remarks.

### 3–5. Booking profit, chemical COGS, overhead
Auto snapshot on Done: visit revenue − chemical − direct expenses − tech cost − overhead = gross profit; company 60% − chemical − expenses − overhead = company net.

### 6–8. Dashboard, reports, alerts
Daily/monthly Accounts dashboard · CSV exports · low stock / expiry / supplier payment / high expense / excess chemical / P&L digests.

## Implementation map

| Area | Backend | CRM |
|------|---------|-----|
| Branches + seed | `accounts` app, `seed_accounts_branches` | Accounts nav |
| Inventory | `/api/accounts/chemicals|suppliers|stock-*` | `/accounts/inventory` |
| Expenses | `/api/accounts/expenses` + ExpenseClaim bridge | `/accounts/expenses` |
| Booking profit | `BookingCostSnapshot`, chemical usages | `/accounts/booking-profit` |
| Partner chemical | `/api/partner/chemicals/`, `.../chemical-usage/` | App can call APIs |
| Overhead / P&L | management commands + `/overhead/allocate/`, `/rebuild-pnl/` | Dashboard buttons |
| Alerts | `run_accounts_alerts`, `/api/accounts/alerts/` | `/accounts/alerts` |
| Reports CSV | `/api/accounts/export/?report=` | `/accounts/reports` |

## Ops commands

```bash
python manage.py migrate accounts
python manage.py seed_accounts_branches
python manage.py allocate_accounts_overhead
python manage.py rebuild_accounts_pnl --days 31
python manage.py run_accounts_alerts
```
