"""Technician ledger/report builder using revenue-model payout snapshots."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.models import (
    JobCard,
    JobCardTechnicianParticipation,
    SettlementLineItem,
    Technician,
    TechnicianSettlement,
)
from core.payment_utils import effective_service_total
from core.payout_engine import is_amc_economics, is_contractual_economics, quantize_money
from core.revenue_constants import (
    CONTRACTUAL_COMMERCIAL_TYPES,
    CONTRACTUAL_PROPERTY_TYPES,
)
from partner.models import PartnerEarning


def _report_date(job: JobCard):
    """
    Use completion date when available, otherwise the scheduled booking date.

    Dates are resolved in the project timezone so a visit closed late in the
    evening is reported on the same day the `__date` filters match it on.
    """
    stamp = job.completed_at or job.schedule_datetime or job.created_at
    return timezone.localtime(stamp).date()


def _economics(job: JobCard) -> str:
    """
    Ledger booking type keys:
    - one_time
    - amc                  (home / private AMC)
    - contract             (commercial / society one-time style contract visit)
    - contract_amc         (commercial / society AMC)
    """
    amc = is_amc_economics(job)
    contract = is_contractual_economics(job)
    if amc and contract:
        return 'contract_amc'
    if amc:
        return 'amc'
    if contract:
        return 'contract'
    return 'one_time'


def _booking_type_label(economics: str) -> str:
    return {
        'one_time': 'One Time',
        'amc': 'AMC',
        'contract': 'Contract One Time',
        'contract_amc': 'Contract AMC',
    }.get(economics, 'One Time')


def _technician_share(job: JobCard, technician: Technician) -> Decimal:
    """Return this technician's immutable payout snapshot for a completed visit."""
    if job.status != JobCard.JobStatus.DONE:
        return Decimal('0.00')
    if technician.technician_type == Technician.TechnicianType.SALARIED:
        return Decimal('0.00')

    participation = next(
        (row for row in job.technician_participations.all() if row.technician_id == technician.id),
        None,
    )
    if participation is not None:
        snap = quantize_money(participation.payout_amount_snapshot)
        # Only trust a positive snapshot — zero used to short-circuit and hide
        # PartnerEarning / visit_payout_amount after held→recalculated payouts.
        if snap > 0:
            return snap

    partner = getattr(technician, 'partner_account', None)
    if partner is not None:
        earning = next(
            (
                row for row in job.partner_earnings.all()
                if row.partner_id == partner.id
                and row.earning_type == PartnerEarning.EarningType.REVENUE_SHARE
            ),
            None,
        )
        if earning is not None and earning.amount:
            return quantize_money(earning.amount)

    if job.technician_id == technician.id:
        if job.visit_payout_amount and job.visit_payout_amount > 0:
            return quantize_money(job.visit_payout_amount)
        # Held jobs: pool was calculated but not allocated — credit sole assigned lead.
        if (
            job.technician_pool_amount
            and job.technician_pool_amount > 0
            and job.payout_status == JobCard.PayoutStatus.HELD
        ):
            return quantize_money(job.technician_pool_amount)
    return Decimal('0.00')


def _line_totals(job: JobCard, technician: Technician) -> tuple[Decimal, Decimal, Decimal]:
    bonus = Decimal('0.00')
    penalty = Decimal('0.00')
    paid = Decimal('0.00')
    settled_earning_ids = set()
    for line in job.settlement_line_items.all():
        if line.settlement.technician_id != technician.id:
            continue
        if line.partner_earning_id:
            settled_earning_ids.add(line.partner_earning_id)
        if line.earning_type == SettlementLineItem.EarningType.INCENTIVE:
            bonus += line.amount
        elif line.earning_type == SettlementLineItem.EarningType.DEDUCTION:
            penalty += line.amount
        if line.settlement.status == TechnicianSettlement.Status.PAID:
            if line.earning_type == SettlementLineItem.EarningType.DEDUCTION:
                paid -= line.amount
            else:
                paid += line.amount

    # Approved bonus/penalty earnings can exist before a settlement batch is built.
    # Include those in payable totals, while avoiding double-counting settled lines.
    partner = getattr(technician, 'partner_account', None)
    if partner is not None:
        for earning in job.partner_earnings.all():
            if earning.partner_id != partner.id or earning.id in settled_earning_ids:
                continue
            if earning.earning_type == PartnerEarning.EarningType.INCENTIVE:
                bonus += earning.amount
            elif earning.earning_type == PartnerEarning.EarningType.DEDUCTION:
                penalty += earning.amount
    return quantize_money(bonus), quantize_money(penalty), quantize_money(max(paid, 0))


def technician_jobs_queryset(technician: Technician):
    participations = JobCardTechnicianParticipation.objects.select_related(
        'technician', 'partner',
    ).filter(technician=technician)
    earnings = PartnerEarning.objects.select_related('partner').filter(
        partner__core_technician=technician,
    )
    settlement_lines = SettlementLineItem.objects.select_related(
        'settlement', 'job', 'participation',
    ).filter(settlement__technician=technician)

    return (
        JobCard.objects.filter(
            Q(technician=technician)
            | Q(technician_participations__technician=technician)
            | Q(partner_earnings__partner__core_technician=technician)
        )
        .select_related('client', 'master_city', 'parent_job')
        .prefetch_related(
            Prefetch('technician_participations', queryset=participations),
            Prefetch('partner_earnings', queryset=earnings),
            Prefetch('settlement_line_items', queryset=settlement_lines),
            'feedbacks',
        )
        .distinct()
    )


def apply_ledger_filters(queryset, params):
    date_from = parse_date(params.get('from') or '')
    date_to = parse_date(params.get('to') or '')
    # Mirrors _report_date: completion date, else schedule date, else created date.
    unscheduled = Q(completed_at__isnull=True, schedule_datetime__isnull=True)
    if date_from:
        queryset = queryset.filter(
            Q(completed_at__date__gte=date_from)
            | Q(completed_at__isnull=True, schedule_datetime__date__gte=date_from)
            | (unscheduled & Q(created_at__date__gte=date_from))
        )
    if date_to:
        queryset = queryset.filter(
            Q(completed_at__date__lte=date_to)
            | Q(completed_at__isnull=True, schedule_datetime__date__lte=date_to)
            | (unscheduled & Q(created_at__date__lte=date_to))
        )

    city = (params.get('city') or '').strip()
    if city:
        queryset = queryset.filter(
            Q(city__iexact=city) | Q(master_city__name__iexact=city)
        )
    service_type = (params.get('service_type') or '').strip()
    if service_type:
        queryset = queryset.filter(service_type__icontains=service_type)
    booking_type = (params.get('booking_type') or '').strip()
    if booking_type:
        contractual_q = (
            Q(job_type=JobCard.JobType.SOCIETY)
            | Q(commercial_type__in=CONTRACTUAL_COMMERCIAL_TYPES)
            | Q(property_type__in=CONTRACTUAL_PROPERTY_TYPES)
        )
        amc_q = (
            Q(service_category=JobCard.ServiceCategory.AMC)
            | Q(is_amc_main_booking=True)
            | Q(included_in_amc=True)
        )
        if booking_type == 'one_time':
            queryset = queryset.exclude(amc_q | contractual_q)
        elif booking_type == 'amc':
            queryset = queryset.filter(amc_q)
        elif booking_type == 'contract':
            queryset = queryset.filter(contractual_q)
    status = (params.get('status') or '').strip()
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def heal_stuck_payouts(jobs) -> int:
    """
    Recalculate Done jobs stuck on Held / blank payment_model so Tech 40% fills in.
    Safe no-op for approved/paid/legacy jobs (engine skips those unless force).
    """
    from core.payout_engine import calculate_and_apply_payout

    healed = 0
    for job in jobs:
        if job.status != JobCard.JobStatus.DONE:
            continue
        if job.payout_status not in (
            JobCard.PayoutStatus.HELD,
            JobCard.PayoutStatus.NOT_APPLICABLE,
            JobCard.PayoutStatus.PENDING,
        ):
            continue
        # Only touch rows that look broken: company/pool set but tech payout empty,
        # or payout still held / never applied.
        pool = job.technician_pool_amount or Decimal('0.00')
        visit_pay = job.visit_payout_amount or Decimal('0.00')
        if job.payout_status == JobCard.PayoutStatus.HELD or (pool > 0 and visit_pay <= 0) or not job.payment_model:
            result = calculate_and_apply_payout(job, force=True)
            if not result.skipped:
                healed += 1
                job.refresh_from_db()
    return healed


def serialize_ledger_row(job: JobCard, technician: Technician) -> dict:
    economics = _economics(job)
    completed = job.status == JobCard.JobStatus.DONE
    booking_amount = quantize_money(effective_service_total(job))
    visit_revenue = quantize_money(job.visit_revenue_amount) if completed else Decimal('0.00')
    if visit_revenue <= 0 and completed and economics == 'one_time':
        visit_revenue = booking_amount
    tech_share = _technician_share(job, technician)
    company_share = quantize_money(job.company_share_amount) if completed else Decimal('0.00')
    # Prefer stored company share. Only synthesize when payout snapshots exist
    # (visit_revenue was set by the engine) so we don't invent company money
    # on legacy jobs that never ran 40/60.
    if company_share <= 0 and completed and visit_revenue > 0 and (job.technician_pool_amount or 0) > 0:
        company_share = quantize_money(max(visit_revenue - tech_share, Decimal('0.00')))
    bonus, penalty, paid = _line_totals(job, technician)
    net = quantize_money(max(tech_share + bonus - penalty, Decimal('0.00')))
    pending = quantize_money(max(net - paid, Decimal('0.00')))
    feedbacks = list(job.feedbacks.all())
    rating = feedbacks[0].rating if feedbacks else None
    planned = job.planned_visit_count or job.max_cycle

    return {
        'job_id': job.id,
        'booking_id': job.code or str(job.id),
        'booking_date': _report_date(job).isoformat(),
        'customer_name': job.client.full_name if job.client_id else '',
        'service_type': job.service_type or '',
        'city': job.master_city.name if job.master_city_id else (job.city or ''),
        'booking_type': economics,
        'booking_type_label': _booking_type_label(economics),
        'status': job.status,
        'is_completed_visit': completed,
        'service_cycle': job.service_cycle,
        'planned_visits': planned,
        'booking_amount': str(booking_amount),
        'visit_revenue': str(visit_revenue),
        'technician_share': str(tech_share),
        'company_share': str(company_share),
        'bonus': str(bonus),
        'penalty': str(penalty),
        'paid_amount': str(paid),
        'pending_amount': str(pending),
        'net_payable': str(net),
        'payout_status': job.payout_status or '',
        'payout_status_label': {
            JobCard.PayoutStatus.PENDING: 'Pending',
            JobCard.PayoutStatus.HELD: 'Held',
            JobCard.PayoutStatus.APPROVED: 'Approved',
            JobCard.PayoutStatus.PAID: 'Paid',
            JobCard.PayoutStatus.CANCELLED: 'Cancelled',
            JobCard.PayoutStatus.NOT_APPLICABLE: 'N/A',
            JobCard.PayoutStatus.LEGACY_EXEMPT: 'Legacy',
        }.get(job.payout_status or '', job.payout_status or '—'),
        'customer_rating': rating,
    }


def summarize_rows(rows: list[dict]) -> dict:
    money_fields = (
        'booking_amount', 'visit_revenue', 'technician_share', 'company_share',
        'bonus', 'penalty', 'paid_amount', 'pending_amount', 'net_payable',
    )
    totals = {field: Decimal('0.00') for field in money_fields}
    job_types = defaultdict(int)
    completed = 0
    ratings = []
    for row in rows:
        # Contract AMC uses AMC visit economics — count it under AMC for summary cards.
        bt = row['booking_type']
        job_types['amc' if bt == 'contract_amc' else bt] += 1
        if row['is_completed_visit']:
            completed += 1
        if row['customer_rating'] is not None:
            ratings.append(Decimal(str(row['customer_rating'])))
        for field in money_fields:
            totals[field] += Decimal(row[field])
    return {
        'total_jobs': len(rows),
        'completed_jobs': completed,
        'one_time_jobs': job_types['one_time'],
        'amc_jobs': job_types['amc'],
        'contract_jobs': job_types['contract'],
        'total_revenue_generated': str(quantize_money(totals['visit_revenue'])),
        'booking_amount': str(quantize_money(totals['booking_amount'])),
        'technician_share': str(quantize_money(totals['technician_share'])),
        'company_share': str(quantize_money(totals['company_share'])),
        'bonus': str(quantize_money(totals['bonus'])),
        'penalty': str(quantize_money(totals['penalty'])),
        'paid_amount': str(quantize_money(totals['paid_amount'])),
        'pending_amount': str(quantize_money(totals['pending_amount'])),
        'net_payable': str(quantize_money(totals['net_payable'])),
        'average_rating': str(
            quantize_money(sum(ratings, Decimal('0.00')) / len(ratings))
            if ratings else Decimal('0.00')
        ),
    }


def earning_periods(technician: Technician) -> dict:
    today = timezone.localdate()
    all_rows = [
        serialize_ledger_row(job, technician)
        for job in technician_jobs_queryset(technician).filter(status=JobCard.JobStatus.DONE)
    ]
    daily = [row for row in all_rows if row['booking_date'] == today.isoformat()]
    monthly = [
        row for row in all_rows
        if row['booking_date'][:7] == today.strftime('%Y-%m')
    ]
    return {
        'daily': summarize_rows(daily)['net_payable'],
        'monthly': summarize_rows(monthly)['net_payable'],
        'lifetime': summarize_rows(all_rows)['net_payable'],
    }


def payment_history(technician: Technician, params) -> list[dict]:
    qs = technician.settlements.select_related('paid_by').all()
    date_from = parse_date(params.get('from') or '')
    date_to = parse_date(params.get('to') or '')
    if date_from:
        qs = qs.filter(period_end__gte=date_from)
    if date_to:
        qs = qs.filter(period_start__lte=date_to)
    return [
        {
            'id': row.id,
            'period_start': row.period_start.isoformat(),
            'period_end': row.period_end.isoformat(),
            'status': row.status,
            'gross_amount': str(row.gross_amount),
            'bonus': str(row.incentive_amount),
            'penalty': str(row.deduction_amount),
            'net_amount': str(row.net_amount),
            'paid_at': row.paid_at.isoformat() if row.paid_at else None,
            'paid_by': (
                row.paid_by.get_full_name() or row.paid_by.username
                if row.paid_by else None
            ),
            'notes': row.notes,
        }
        for row in qs.order_by('-period_end', '-id')[:100]
    ]
