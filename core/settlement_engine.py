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
        .exclude(job__hidden_from_technician_ledger=True)
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

    # Mark each job PAID only when EVERY eligible partner tech on that job
    # already has a paid revenue-share settlement line. Otherwise keep APPROVED
    # so co-technicians can still settle their own share.
    job_ids = list(settlement.line_items.values_list('job_id', flat=True).distinct())
    jobs = (
        JobCard.objects.filter(id__in=job_ids)
        .exclude(payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT)
        .prefetch_related(
            'technician_participations__technician',
            'settlement_line_items__settlement',
        )
    )
    fully_paid_ids = []
    partially_paid_ids = []
    for job in jobs:
        eligible_tech_ids = {
            p.technician_id
            for p in job.technician_participations.all()
            if p.technician_id
            and p.is_payout_eligible
            and getattr(p.technician, 'technician_type', None) == Technician.TechnicianType.PARTNER
        }
        if not eligible_tech_ids and job.technician_id:
            # Lead-only jobs without participation rows
            if getattr(job.technician, 'technician_type', None) == Technician.TechnicianType.PARTNER:
                eligible_tech_ids = {job.technician_id}
        settled_tech_ids = {
            line.settlement.technician_id
            for line in job.settlement_line_items.all()
            if line.settlement.status == TechnicianSettlement.Status.PAID
            and line.earning_type == SettlementLineItem.EarningType.REVENUE_SHARE
            and line.settlement.technician_id
        }
        if eligible_tech_ids and eligible_tech_ids.issubset(settled_tech_ids):
            fully_paid_ids.append(job.id)
        else:
            partially_paid_ids.append(job.id)

    if fully_paid_ids:
        JobCard.objects.filter(id__in=fully_paid_ids).update(
            payout_status=JobCard.PayoutStatus.PAID,
        )
    if partially_paid_ids:
        JobCard.objects.filter(id__in=partially_paid_ids).exclude(
            payout_status=JobCard.PayoutStatus.PAID,
        ).update(payout_status=JobCard.PayoutStatus.APPROVED)

    from core.revenue_audit import log_revenue_event
    log_revenue_event(
        action='settlement_marked_paid',
        booking_id=str(settlement.id),
        details={'technician_id': settlement.technician_id, 'net_amount': str(settlement.net_amount)},
        user=user,
    )
    return settlement


@transaction.atomic
def settle_jobs_for_technician(
    *,
    technician: Technician,
    job_ids: list[int],
    user=None,
    notes: str = '',
) -> TechnicianSettlement:
    """
    Settle selected completed ledger jobs for one technician in a single batch.

    Creates settlement lines from participation snapshots / PartnerEarnings,
    then marks the settlement Approved + Paid. Jobs stay on the ledger —
    they are never deleted. Multi-tech jobs stay settleable per technician
    until each partner's share is paid.
    """
    if not is_revenue_model_enabled():
        raise SettlementError('REVENUE_MODEL_V2 is disabled', code='feature_flag_off')
    ids = [int(x) for x in (job_ids or []) if x]
    if not ids:
        raise SettlementError('Select at least one booking to settle', code='empty_selection')

    from core.payout_engine import calculate_and_apply_payout
    from partner.models import PartnerEarning

    jobs = list(
        JobCard.objects.select_related('technician', 'partner')
        .prefetch_related('technician_participations', 'partner_earnings', 'settlement_line_items__settlement')
        .filter(id__in=ids, status=JobCard.JobStatus.DONE)
        .exclude(hidden_from_technician_ledger=True)
    )
    if not jobs:
        raise SettlementError('No completed bookings found for settlement', code='no_jobs')

    today = timezone.localdate()
    partner = getattr(technician, 'partner_account', None)
    settlement = TechnicianSettlement.objects.create(
        technician=technician,
        partner=partner if partner and getattr(partner, 'is_active', True) else None,
        period_start=today,
        period_end=today,
        cadence=SETTLEMENT_CADENCE_WEEKLY,
        status=TechnicianSettlement.Status.DRAFT,
        notes=notes or f'Ledger settle {today.isoformat()} ({len(ids)} jobs)',
    )

    lines_created = 0
    for job in jobs:
        # Per-technician only — co-techs must still be able to settle their share.
        already_paid = any(
            line.settlement.technician_id == technician.id
            and line.settlement.status == TechnicianSettlement.Status.PAID
            and line.earning_type == SettlementLineItem.EarningType.REVENUE_SHARE
            for line in job.settlement_line_items.all()
        )
        if already_paid:
            continue

        if job.payout_status in (
            JobCard.PayoutStatus.HELD,
            JobCard.PayoutStatus.PENDING,
            JobCard.PayoutStatus.NOT_APPLICABLE,
            JobCard.PayoutStatus.APPROVED,
            '',
            None,
        ):
            # Recalc when this tech still has no snapshot (even if co-tech already settled).
            participation = next(
                (p for p in job.technician_participations.all() if p.technician_id == technician.id),
                None,
            )
            snap = (
                quantize_money(participation.payout_amount_snapshot)
                if participation and participation.payout_amount_snapshot
                else Decimal('0.00')
            )
            if snap <= 0 and job.payout_status != JobCard.PayoutStatus.PAID:
                calculate_and_apply_payout(job, force=True)
                job.refresh_from_db()

        participation = next(
            (p for p in job.technician_participations.all() if p.technician_id == technician.id),
            None,
        )
        amount = Decimal('0.00')
        earning = None
        if partner:
            earning = next(
                (
                    e for e in job.partner_earnings.all()
                    if e.partner_id == partner.id
                    and e.earning_type == PartnerEarning.EarningType.REVENUE_SHARE
                ),
                None,
            )
            if earning:
                amount = quantize_money(earning.amount)
                if not earning.is_approved:
                    earning.is_approved = True
                    earning.save(update_fields=['is_approved'])
        if amount <= 0 and participation and participation.payout_amount_snapshot:
            amount = quantize_money(participation.payout_amount_snapshot)
        if amount <= 0 and job.technician_id == technician.id and job.visit_payout_amount:
            # Sole lead fallback — never give full pool when multiple partners exist.
            eligible = [
                p for p in job.technician_participations.all()
                if p.is_payout_eligible
                and getattr(p.technician, 'technician_type', None) == Technician.TechnicianType.PARTNER
            ]
            if len(eligible) <= 1:
                amount = quantize_money(job.visit_payout_amount)
        if amount <= 0:
            continue

        # Avoid double OneToOne partner_earning link if already on another open settlement
        pe_link = earning
        if pe_link is not None:
            from core.models import SettlementLineItem as SLI
            if SLI.objects.filter(partner_earning=pe_link).exists():
                pe_link = None

        SettlementLineItem.objects.create(
            settlement=settlement,
            job=job,
            participation=participation,
            partner_earning=pe_link,
            earning_type=SettlementLineItem.EarningType.REVENUE_SHARE,
            amount=amount,
            notes=f'Ledger settle Job #{job.code or job.id}',
        )
        lines_created += 1

    if lines_created == 0:
        settlement.status = TechnicianSettlement.Status.CANCELLED
        settlement.save(update_fields=['status', 'updated_at'])
        raise SettlementError(
            'Selected bookings are already settled or have ₹0 tech share',
            code='nothing_to_settle',
        )

    settlement.recompute_totals()
    settlement.status = TechnicianSettlement.Status.PENDING_APPROVAL
    settlement.save(update_fields=[
        'gross_amount', 'incentive_amount', 'deduction_amount', 'net_amount',
        'status', 'updated_at',
    ])
    approve_settlement(settlement, user=user)
    return mark_settlement_paid(settlement, user=user)


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
