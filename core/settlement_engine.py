"""
Build and transition technician settlements from approved PartnerEarnings.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from typing import Iterable, Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import JobCard, SettlementLineItem, Technician, TechnicianSettlement
from core.payout_engine import is_revenue_model_enabled, quantize_money
from core.revenue_constants import SETTLEMENT_CADENCE_MONTHLY, SETTLEMENT_CADENCE_WEEKLY

logger = logging.getLogger(__name__)


class SettlementError(Exception):
    def __init__(self, message: str, code: str = 'settlement_error'):
        super().__init__(message)
        self.message = message
        self.code = code


def _as_aware_range(period_start: date, period_end: date):
    start_dt = timezone.make_aware(datetime.combine(period_start, time.min))
    end_dt = timezone.make_aware(datetime.combine(period_end, time.max))
    return start_dt, end_dt


def _resolve_technician_for_earning(earning) -> Optional[Technician]:
    if earning.participation_id and earning.participation.technician_id:
        return earning.participation.technician
    partner = earning.partner
    tech = getattr(partner, 'core_technician', None)
    return tech


def eligible_earnings_queryset(*, period_start: date, period_end: date):
    """Approved earnings in period, not yet on an active settlement, non-legacy jobs."""
    from partner.models import PartnerEarning

    start_dt, end_dt = _as_aware_range(period_start, period_end)
    return (
        PartnerEarning.objects.select_related(
            'partner',
            'partner__core_technician',
            'job',
            'participation',
            'participation__technician',
        )
        .filter(
            is_approved=True,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        )
        .filter(
            Q(job__payout_status__in=[
                JobCard.PayoutStatus.APPROVED,
                JobCard.PayoutStatus.PENDING,
                JobCard.PayoutStatus.PAID,
            ])
            | Q(job__payout_status=JobCard.PayoutStatus.HELD, is_approved=True)
        )
        .exclude(job__payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT)
        .filter(settlement_line__isnull=True)
        .order_by('id')
    )


@transaction.atomic
def build_settlements_for_period(
    *,
    period_start: date,
    period_end: date,
    cadence: str = SETTLEMENT_CADENCE_WEEKLY,
    technician_ids: Optional[Iterable[int]] = None,
    created_by=None,
) -> list[TechnicianSettlement]:
    if not is_revenue_model_enabled():
        raise SettlementError('REVENUE_MODEL_V2 is disabled', code='feature_flag_off')
    if period_end < period_start:
        raise SettlementError('period_end must be on/after period_start', code='invalid_period')
    if cadence not in (SETTLEMENT_CADENCE_WEEKLY, SETTLEMENT_CADENCE_MONTHLY):
        raise SettlementError('cadence must be weekly or monthly', code='invalid_cadence')

    earnings = list(eligible_earnings_queryset(period_start=period_start, period_end=period_end))
    grouped: dict[int, list] = defaultdict(list)
    for earning in earnings:
        tech = _resolve_technician_for_earning(earning)
        if not tech:
            continue
        if technician_ids is not None and tech.id not in set(technician_ids):
            continue
        grouped[tech.id].append(earning)

    created: list[TechnicianSettlement] = []
    for tech_id, rows in grouped.items():
        tech = Technician.objects.get(pk=tech_id)
        partner = getattr(tech, 'partner_account', None)
        settlement = TechnicianSettlement.objects.create(
            technician=tech,
            partner=partner if partner and partner.is_active else None,
            period_start=period_start,
            period_end=period_end,
            cadence=cadence,
            status=TechnicianSettlement.Status.DRAFT,
            notes=f'Auto-built {timezone.now().isoformat()}',
        )
        for earning in rows:
            line_type = earning.earning_type
            if line_type not in dict(SettlementLineItem.EarningType.choices):
                line_type = SettlementLineItem.EarningType.REVENUE_SHARE
            SettlementLineItem.objects.create(
                settlement=settlement,
                job=earning.job,
                participation=earning.participation,
                partner_earning=earning,
                earning_type=line_type,
                amount=quantize_money(earning.amount),
                notes=f'Job #{earning.job.code}',
            )
        settlement.recompute_totals()
        settlement.status = TechnicianSettlement.Status.PENDING_APPROVAL
        settlement.save(update_fields=[
            'gross_amount', 'incentive_amount', 'deduction_amount', 'net_amount',
            'status', 'updated_at',
        ])
        created.append(settlement)
        logger.info(
            'Built settlement #%s tech=%s lines=%s net=%s',
            settlement.id,
            tech_id,
            len(rows),
            settlement.net_amount,
        )
        from core.revenue_audit import log_revenue_event
        log_revenue_event(
            action='settlement_built',
            booking_id=str(settlement.id),
            details={
                'technician_id': tech_id,
                'period_start': str(period_start),
                'period_end': str(period_end),
                'net_amount': str(settlement.net_amount),
                'lines': len(rows),
            },
            user=created_by if getattr(created_by, 'pk', None) else None,
        )
    return created


@transaction.atomic
def approve_settlement(settlement: TechnicianSettlement, *, user=None) -> TechnicianSettlement:
    settlement = TechnicianSettlement.objects.select_for_update().get(pk=settlement.pk)
    if settlement.status not in (
        TechnicianSettlement.Status.DRAFT,
        TechnicianSettlement.Status.PENDING_APPROVAL,
    ):
        raise SettlementError(
            f'Cannot approve settlement in status={settlement.status}',
            code='invalid_status',
        )
    settlement.status = TechnicianSettlement.Status.APPROVED
    settlement.approved_at = timezone.now()
    settlement.approved_by = user
    settlement.save(update_fields=['status', 'approved_at', 'approved_by', 'updated_at'])

    from partner.models import PartnerEarning

    earning_ids = list(
        settlement.line_items.exclude(partner_earning_id=None)
        .values_list('partner_earning_id', flat=True)
    )
    if earning_ids:
        PartnerEarning.objects.filter(id__in=earning_ids).update(is_approved=True)

    job_ids = list(settlement.line_items.values_list('job_id', flat=True))
    JobCard.objects.filter(
        id__in=job_ids,
        payout_status__in=[
            JobCard.PayoutStatus.PENDING,
            JobCard.PayoutStatus.HELD,
            JobCard.PayoutStatus.APPROVED,
        ],
    ).exclude(payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT).update(
        payout_status=JobCard.PayoutStatus.APPROVED,
    )
    from core.revenue_audit import log_revenue_event
    log_revenue_event(
        action='settlement_approved',
        booking_id=str(settlement.id),
        details={'technician_id': settlement.technician_id, 'net_amount': str(settlement.net_amount)},
        user=user,
    )
    return settlement


@transaction.atomic
def mark_settlement_paid(settlement: TechnicianSettlement, *, user=None) -> TechnicianSettlement:
    settlement = TechnicianSettlement.objects.select_for_update().get(pk=settlement.pk)
    if settlement.status != TechnicianSettlement.Status.APPROVED:
        raise SettlementError(
            f'Cannot mark paid when status={settlement.status}',
            code='invalid_status',
        )
    settlement.status = TechnicianSettlement.Status.PAID
    settlement.paid_at = timezone.now()
    settlement.paid_by = user
    settlement.save(update_fields=['status', 'paid_at', 'paid_by', 'updated_at'])

    job_ids = list(settlement.line_items.values_list('job_id', flat=True))
    JobCard.objects.filter(id__in=job_ids).exclude(
        payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT
    ).update(payout_status=JobCard.PayoutStatus.PAID)
    from core.revenue_audit import log_revenue_event
    log_revenue_event(
        action='settlement_marked_paid',
        booking_id=str(settlement.id),
        details={'technician_id': settlement.technician_id, 'net_amount': str(settlement.net_amount)},
        user=user,
    )
    return settlement


@transaction.atomic
def cancel_settlement(settlement: TechnicianSettlement) -> TechnicianSettlement:
    settlement = TechnicianSettlement.objects.select_for_update().get(pk=settlement.pk)
    if settlement.status == TechnicianSettlement.Status.PAID:
        raise SettlementError('Paid settlements cannot be cancelled', code='already_paid')
    # Detach earnings so they can be re-batched
    for line in settlement.line_items.select_related('partner_earning'):
        if line.partner_earning_id:
            # OneToOne reverse: clear by deleting line linkage
            pe = line.partner_earning
            line.partner_earning = None
            line.save(update_fields=['partner_earning', 'updated_at'])
            # No FK on PartnerEarning to clear — OneToOne is on SettlementLineItem
            _ = pe
    settlement.status = TechnicianSettlement.Status.CANCELLED
    settlement.save(update_fields=['status', 'updated_at'])
    from core.revenue_audit import log_revenue_event
    log_revenue_event(
        action='settlement_cancelled',
        booking_id=str(settlement.id),
        details={'technician_id': settlement.technician_id},
    )
    return settlement
