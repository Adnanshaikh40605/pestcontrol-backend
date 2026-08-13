"""Monthly office/marketing overhead ÷ completed bookings."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from accounts.models import Branch, ExpenseCategory, ExpenseEntry, MonthlyOverheadRate
from accounts.services.profit import recalculate_booking_cost
from core.models import JobCard
from core.payout_engine import quantize_money


def allocate_monthly_overhead(
    *,
    year: int | None = None,
    month: int | None = None,
    branch: Branch | None = None,
    recompute_snapshots: bool = True,
) -> list[MonthlyOverheadRate]:
    today = timezone.localdate()
    year = year or today.year
    month = month or today.month
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    branches = [branch] if branch else list(Branch.objects.filter(is_active=True))
    results: list[MonthlyOverheadRate] = []

    for br in branches:
        overhead_total = ExpenseEntry.objects.filter(
            branch=br,
            status=ExpenseEntry.Status.POSTED,
            entry_date__gte=start,
            entry_date__lte=end,
        ).filter(
            models_q_overhead()
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        completed = JobCard.objects.filter(
            status=JobCard.JobStatus.DONE,
            schedule_datetime__date__gte=start,
            schedule_datetime__date__lte=end,
        )
        # Prefer city map; fall back to all Done in range for single-branch setups
        from accounts.models import BranchCityMap

        city_ids = list(BranchCityMap.objects.filter(branch=br).values_list('city_id', flat=True))
        if city_ids:
            completed = completed.filter(master_city_id__in=city_ids)
        booking_count = completed.count()
        per = (
            quantize_money(Decimal(overhead_total) / Decimal(booking_count))
            if booking_count
            else Decimal('0.00')
        )
        rate, _ = MonthlyOverheadRate.objects.update_or_create(
            branch=br,
            year=year,
            month=month,
            defaults={
                'total_overhead': quantize_money(overhead_total),
                'completed_bookings': booking_count,
                'overhead_per_booking': per,
            },
        )
        results.append(rate)

        if recompute_snapshots and booking_count:
            for job_id in completed.values_list('id', flat=True):
                recalculate_booking_cost(job_id)

    return results


def models_q_overhead():
    from django.db.models import Q

    return (
        Q(category__is_overhead=True)
        | Q(category__group__in=[ExpenseCategory.Group.OFFICE, ExpenseCategory.Group.MARKETING])
    )
