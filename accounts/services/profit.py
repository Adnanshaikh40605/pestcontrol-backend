"""Booking-wise cost snapshot calculator (gross + company net profit)."""
from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from accounts.models import (
    BookingCostSnapshot,
    ChemicalUsage,
    ExpenseCategory,
    ExpenseEntry,
    MonthlyOverheadRate,
)
from accounts.services.stock import resolve_branch_for_job
from core.models import JobCard
from core.payment_utils import effective_service_total
from core.payout_engine import quantize_money


def _pct(part: Decimal, whole: Decimal) -> Decimal:
    if not whole or whole == 0:
        return Decimal('0.00')
    return quantize_money((part / whole) * Decimal('100'))


def recalculate_booking_cost(job: JobCard | int) -> BookingCostSnapshot | None:
    if isinstance(job, int):
        job = JobCard.objects.filter(pk=job).first()
    if not job:
        return None

    branch = resolve_branch_for_job(job)
    booking_date = timezone.localtime(
        job.schedule_datetime or job.completed_at or job.created_at
    ).date()

    visit_revenue = quantize_money(job.visit_revenue_amount or effective_service_total(job) or 0)
    booking_amount = quantize_money(effective_service_total(job) or visit_revenue)
    company_share = quantize_money(job.company_share_amount or 0)
    technician_cost = quantize_money(job.technician_pool_amount or job.visit_payout_amount or 0)

    chemical_cost = quantize_money(
        ChemicalUsage.objects.filter(jobcard=job).aggregate(total=Sum('line_cost'))['total'] or 0
    )

    direct_expense_cost = quantize_money(
        ExpenseEntry.objects.filter(
            jobcard=job,
            status=ExpenseEntry.Status.POSTED,
            category__group=ExpenseCategory.Group.TECHNICIAN,
        ).aggregate(total=Sum('amount'))['total']
        or 0
    )

    overhead_cost = Decimal('0.00')
    if branch:
        rate = MonthlyOverheadRate.objects.filter(
            branch=branch,
            year=booking_date.year,
            month=booking_date.month,
        ).first()
        if rate:
            overhead_cost = quantize_money(rate.overhead_per_booking)

    total_cost = quantize_money(
        chemical_cost + direct_expense_cost + technician_cost + overhead_cost
    )
    base = visit_revenue if visit_revenue > 0 else booking_amount
    gross_profit = quantize_money(base - total_cost)
    company_net_profit = quantize_money(
        company_share - chemical_cost - direct_expense_cost - overhead_cost
    )

    snapshot, _ = BookingCostSnapshot.objects.update_or_create(
        jobcard=job,
        defaults={
            'branch': branch,
            'booking_date': booking_date,
            'booking_amount': booking_amount,
            'visit_revenue': visit_revenue,
            'chemical_cost': chemical_cost,
            'direct_expense_cost': direct_expense_cost,
            'technician_cost': technician_cost,
            'company_share': company_share,
            'overhead_cost': overhead_cost,
            'total_cost': total_cost,
            'gross_profit': gross_profit,
            'company_net_profit': company_net_profit,
            'gross_margin_percent': _pct(gross_profit, base),
            'company_margin_percent': _pct(company_net_profit, company_share or base),
            'cost_percent': _pct(total_cost, base),
        },
    )
    return snapshot
