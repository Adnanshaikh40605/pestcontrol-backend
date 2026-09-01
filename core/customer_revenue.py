"""Customer profile / revenue summary helpers (CRM customer-history API)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator

from core.payment_utils import effective_service_total, parse_jobcard_price


@dataclass(frozen=True)
class RevenueContribution:
    amount: Decimal
    is_amc: bool
    service: str
    dedupe_key: tuple
    counts_as_booking: bool = False


def _line_is_amc(plan: str) -> bool:
    from core.booking_schedule_engine import is_amc_plan

    return is_amc_plan(plan or '')


def iter_revenue_contributions(job) -> Iterator[RevenueContribution]:
    """
    Expand a JobCard into revenue lines for Customer Profile stats.

    Multi-service package shells are split per ``service_items`` row so Termite
    one-time and Cockroach AMC are never merged into one AMC total.
    """
    from core.booking_schedule_engine import is_multi_service_booking
    from core.complaint_service import is_billable_root_booking, is_complaint_job
    from core.models import JobCard

    if job.status == JobCard.JobStatus.CANCELLED:
        return

    if is_complaint_job(job) or job.included_in_amc or job.is_followup_visit:
        return

    if job.parent_job_id:
        return

    if is_multi_service_booking(job):
        items = job.service_items if isinstance(job.service_items, list) else []
        if not items:
            amount = effective_service_total(job)
            if amount > 0:
                yield RevenueContribution(
                    amount=amount,
                    is_amc=job.service_category == JobCard.ServiceCategory.AMC,
                    service=(job.service_type or '').strip(),
                    dedupe_key=((job.service_type or '').strip(), job.id, amount),
                    counts_as_booking=True,
                )
            return

        for item in items:
            if not isinstance(item, dict):
                continue
            service = str(item.get('service') or '').strip()
            plan = str(item.get('plan') or item.get('frequency') or '')
            amount = parse_jobcard_price(item.get('amount'))
            if amount <= 0:
                continue
            yield RevenueContribution(
                amount=amount,
                is_amc=_line_is_amc(plan),
                service=service,
                dedupe_key=(service, job.id, amount),
                counts_as_booking=True,
            )
        return

    if not is_billable_root_booking(job):
        return

    amount = effective_service_total(job)
    if amount <= 0:
        price_str = str(job.price or '').replace('₹', '').replace(',', '').strip()
        amount = parse_jobcard_price(price_str)
    if amount <= 0:
        return

    yield RevenueContribution(
        amount=amount,
        is_amc=job.service_category == JobCard.ServiceCategory.AMC,
        service=(job.service_type or '').strip(),
        dedupe_key=((job.service_type or '').strip(), job.id, amount),
        counts_as_booking=True,
    )


def count_billable_booking_units(job) -> int:
    """How many original bookings this row represents in customer stats."""
    from core.booking_schedule_engine import is_multi_service_booking
    from core.complaint_service import is_billable_root_booking

    if not is_billable_root_booking(job):
        return 0
    if is_multi_service_booking(job):
        items = job.service_items if isinstance(job.service_items, list) else []
        lines = [
            item for item in items
            if isinstance(item, dict) and parse_jobcard_price(item.get('amount')) > 0
        ]
        return len(lines) if lines else 1
    return 1


def service_line_breakdown(job) -> list[dict]:
    """Per-service amounts for multi-service shells (CRM booking history UI)."""
    from core.booking_schedule_engine import is_multi_service_booking
    from core.models import JobCard

    if not is_multi_service_booking(job):
        return []

    items = job.service_items if isinstance(job.service_items, list) else []
    children = {
        (c.source_service or c.service_type or '').strip().lower(): c
        for c in JobCard.objects.filter(parent_job=job, service_cycle=1)
    }
    lines: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        service = str(item.get('service') or '').strip()
        plan = str(item.get('plan') or item.get('frequency') or '')
        amount = parse_jobcard_price(item.get('amount'))
        child = children.get(service.lower())
        lines.append({
            'service': service,
            'plan': plan,
            'amount': str(amount),
            'is_amc': _line_is_amc(plan),
            'child_booking_id': child.id if child else None,
        })
    return lines
