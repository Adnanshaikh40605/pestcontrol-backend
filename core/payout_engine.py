"""
Revenue Model v2 payout calculator.

One-Time: visit_payout = final_amount × tech_share%
AMC visit: visit_value = package_total / visit_count; payout = visit_value × tech_share%
Contractual: same 40% pool, split equally among eligible partner attendees.
Salaried techs are excluded from the divisor. Zero eligible partners → held.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.revenue_constants import (
    COMPANY_SHARE_PERCENT,
    CONTRACTUAL_COMMERCIAL_TYPES,
    CONTRACTUAL_PROPERTY_TYPES,
    MONEY_QUANTUM,
    TECHNICIAN_SHARE_PERCENT,
)

logger = logging.getLogger(__name__)


def is_revenue_model_enabled() -> bool:
    return bool(getattr(settings, 'REVENUE_MODEL_V2', False))


def quantize_money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM)


def split_pool_equally(pool: Decimal, count: int) -> list[Decimal]:
    """
    Deterministic paise allocation so shares always sum to pool.
    Example: 400 / 3 → [133.34, 133.33, 133.33]
    """
    pool = quantize_money(pool)
    if count <= 0:
        return []
    if count == 1:
        return [pool]
    base = (pool / Decimal(count)).quantize(MONEY_QUANTUM, rounding=ROUND_DOWN)
    amounts = [base] * count
    remainder = pool - (base * count)
    i = 0
    while remainder > 0 and i < count:
        amounts[i] = quantize_money(amounts[i] + MONEY_QUANTUM)
        remainder = quantize_money(remainder - MONEY_QUANTUM)
        i += 1
    return amounts


def revenue_fields_from_parent(parent) -> dict:
    """Copy revenue-model fields onto AMC/child visits."""
    return {
        'package_tier': parent.package_tier or '',
        'payment_model': parent.payment_model or '',
        'technician_share_percent': parent.technician_share_percent or TECHNICIAN_SHARE_PERCENT,
        'company_share_percent': parent.company_share_percent or COMPANY_SHARE_PERCENT,
        'planned_visit_count': parent.planned_visit_count or parent.max_cycle,
        'payout_status': parent.payout_status,
        'discount_amount': parent.discount_amount or 0,
    }


def apply_revenue_defaults_for_new_booking(validated_data: dict) -> dict:
    """Mutate create payload when feature flag is on (conflict-safe defaults)."""
    if not is_revenue_model_enabled():
        return validated_data
    from core.models import JobCard

    if not validated_data.get('payout_status'):
        validated_data['payout_status'] = JobCard.PayoutStatus.NOT_APPLICABLE
    if not validated_data.get('payment_model'):
        validated_data['payment_model'] = JobCard.PaymentModel.REVENUE_SHARING
    validated_data.setdefault('technician_share_percent', TECHNICIAN_SHARE_PERCENT)
    validated_data.setdefault('company_share_percent', COMPANY_SHARE_PERCENT)
    return validated_data


@dataclass
class ParticipantPayout:
    participation_id: Optional[int]
    technician_id: int
    partner_id: Optional[int]
    amount: Decimal
    share_percent: Decimal


@dataclass
class PayoutResult:
    skipped: bool = False
    reason: str = ''
    economics: str = ''  # one_time | amc | contractual | salaried
    visit_revenue: Decimal = Decimal('0.00')
    technician_pool: Decimal = Decimal('0.00')
    company_share: Decimal = Decimal('0.00')
    payout_status: str = ''
    participant_payouts: list[ParticipantPayout] = field(default_factory=list)


def _billable_total(job) -> Decimal:
    from core.payment_utils import effective_service_total, parse_jobcard_price

    total = effective_service_total(job)
    if total and total > 0:
        return quantize_money(total)
    return quantize_money(parse_jobcard_price(job.price))


def _package_root(job):
    """Root booking that owns package total / visit count for AMC children."""
    root = job
    seen = set()
    while root.parent_job_id and root.parent_job_id not in seen:
        seen.add(root.id)
        root = root.parent_job
    return root


def _visit_divisor(job, root) -> int:
    for candidate in (
        job.planned_visit_count,
        root.planned_visit_count,
        root.max_cycle,
        job.max_cycle,
    ):
        if candidate and int(candidate) > 0:
            return int(candidate)
    return 1


def is_amc_economics(job) -> bool:
    from core.models import JobCard

    if job.service_category == JobCard.ServiceCategory.AMC:
        return True
    if job.included_in_amc or job.is_followup_visit or job.is_amc_main_booking:
        return True
    if job.booking_type in (
        JobCard.BookingType.AMC_MAIN,
        JobCard.BookingType.AMC_FOLLOWUP,
    ):
        return True
    root = _package_root(job)
    if root.id != job.id and root.service_category == JobCard.ServiceCategory.AMC:
        return True
    return False


def is_contractual_economics(job) -> bool:
    from core.models import JobCard

    if job.job_type == JobCard.JobType.SOCIETY:
        return True
    if (job.commercial_type or '') in CONTRACTUAL_COMMERCIAL_TYPES:
        return True
    if (job.property_type or '') in CONTRACTUAL_PROPERTY_TYPES:
        return True
    return False


def _tech_share_percent(job) -> Decimal:
    pct = job.technician_share_percent
    if pct is None:
        return TECHNICIAN_SHARE_PERCENT
    return Decimal(str(pct))


def _company_share_percent(job) -> Decimal:
    pct = job.company_share_percent
    if pct is None:
        return COMPANY_SHARE_PERCENT
    return Decimal(str(pct))


def ensure_lead_participation(job) -> Optional[object]:
    """Ensure JobCard.technician has a participation row (lead)."""
    from core.models import JobCardTechnicianParticipation, Technician

    if not job.technician_id:
        # Partner-only assignment: map via partner.core_technician if present
        partner = getattr(job, 'partner', None)
        tech = getattr(partner, 'core_technician', None) if partner else None
        if not tech:
            return None
        technician = tech
    else:
        technician = job.technician

    partner = job.partner
    if partner is None:
        partner = getattr(technician, 'partner_account', None)

    is_salaried = technician.technician_type == Technician.TechnicianType.SALARIED
    defaults = {
        'partner': partner,
        'role': JobCardTechnicianParticipation.Role.LEAD,
        'attendance_status': JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
        'checked_out_at': timezone.now(),
        'is_payout_eligible': not is_salaried,
    }
    row, created = JobCardTechnicianParticipation.objects.get_or_create(
        jobcard=job,
        technician=technician,
        defaults=defaults,
    )
    if not created:
        update_fields = []
        if row.role != JobCardTechnicianParticipation.Role.LEAD:
            row.role = JobCardTechnicianParticipation.Role.LEAD
            update_fields.append('role')
        if row.attendance_status == JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED:
            row.attendance_status = JobCardTechnicianParticipation.AttendanceStatus.COMPLETED
            update_fields.append('attendance_status')
        if partner and row.partner_id != partner.id:
            row.partner = partner
            update_fields.append('partner')
        if row.is_payout_eligible == is_salaried:
            row.is_payout_eligible = not is_salaried
            update_fields.append('is_payout_eligible')
        if update_fields:
            row.save(update_fields=update_fields + ['updated_at'])
    return row


def _eligible_partner_participations(job) -> list:
    from core.models import JobCardTechnicianParticipation, Technician

    attended = {
        JobCardTechnicianParticipation.AttendanceStatus.CHECKED_IN,
        JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
    }
    rows = list(
        job.technician_participations.select_related('technician', 'partner').filter(
            attendance_status__in=attended,
            is_payout_eligible=True,
        )
    )
    eligible = []
    for row in rows:
        tech = row.technician
        if tech.technician_type == Technician.TechnicianType.SALARIED:
            continue
        # Prefer linked partner for ledger; allow partner FK on participation
        if not row.partner_id and not getattr(tech, 'partner_account', None):
            # Partner-type tech without Partner account cannot receive PartnerEarning
            continue
        eligible.append(row)
    return eligible


def _resolve_partner_for_row(row):
    if row.partner_id:
        return row.partner
    return getattr(row.technician, 'partner_account', None)


@transaction.atomic
def calculate_and_apply_payout(job, *, force: bool = False) -> PayoutResult:
    """
    Idempotent payout application after job completion.
    Safe no-op when flag off, legacy_exempt, or payment_model not revenue_sharing.
    """
    from core.models import JobCard, JobCardTechnicianParticipation
    from partner.models import PartnerEarning

    JobCard.objects.select_for_update().filter(pk=job.pk).exists()
    job = JobCard.objects.select_related(
        'technician',
        'partner',
        'parent_job',
        'partner__core_technician',
        'technician__partner_account',
    ).prefetch_related(
        'technician_participations__technician',
        'technician_participations__partner',
    ).get(pk=job.pk)

    if not is_revenue_model_enabled() and not force:
        return PayoutResult(skipped=True, reason='feature_flag_off')

    if job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT:
        return PayoutResult(skipped=True, reason='legacy_exempt', payout_status=job.payout_status)

    if job.payout_status in (
        JobCard.PayoutStatus.APPROVED,
        JobCard.PayoutStatus.PAID,
        JobCard.PayoutStatus.CANCELLED,
    ) and not force:
        return PayoutResult(skipped=True, reason='payout_locked', payout_status=job.payout_status)

    payment_model = (job.payment_model or '').strip()
    if payment_model == JobCard.PaymentModel.SALARIED:
        job.visit_revenue_amount = Decimal('0.00')
        job.technician_pool_amount = Decimal('0.00')
        job.company_share_amount = Decimal('0.00')
        job.visit_payout_amount = Decimal('0.00')
        job.payout_status = JobCard.PayoutStatus.NOT_APPLICABLE
        job.save(update_fields=[
            'visit_revenue_amount', 'technician_pool_amount', 'company_share_amount',
            'visit_payout_amount', 'payout_status', 'updated_at',
        ])
        return PayoutResult(
            skipped=False,
            economics='salaried',
            payout_status=job.payout_status,
            reason='salaried_no_visit_ledger',
        )

    if payment_model != JobCard.PaymentModel.REVENUE_SHARING:
        return PayoutResult(skipped=True, reason='payment_model_not_revenue_sharing', payout_status=job.payout_status)

    ensure_lead_participation(job)
    job.refresh_from_db()

    tech_pct = _tech_share_percent(job)
    company_pct = _company_share_percent(job)
    root = _package_root(job)

    if is_amc_economics(job):
        economics = 'amc'
        package_total = _billable_total(root)
        divisor = _visit_divisor(job, root)
        visit_revenue = quantize_money(package_total / Decimal(divisor))
    elif is_contractual_economics(job):
        economics = 'contractual'
        package_total = _billable_total(root)
        divisor = _visit_divisor(job, root)
        visit_revenue = quantize_money(package_total / Decimal(divisor))
    else:
        economics = 'one_time'
        visit_revenue = _billable_total(job)

    technician_pool = quantize_money(visit_revenue * tech_pct / Decimal('100'))
    company_share = quantize_money(visit_revenue * company_pct / Decimal('100'))
    # Fix rounding so pool + company ≈ visit (prefer pool exact for payouts)
    company_share = quantize_money(visit_revenue - technician_pool)

    eligible = _eligible_partner_participations(job)
    result = PayoutResult(
        economics=economics,
        visit_revenue=visit_revenue,
        technician_pool=technician_pool,
        company_share=company_share,
    )

    if not eligible:
        job.visit_revenue_amount = visit_revenue
        job.technician_pool_amount = technician_pool
        job.company_share_amount = company_share
        job.visit_payout_amount = Decimal('0.00')
        job.payout_status = JobCard.PayoutStatus.HELD
        job.save(update_fields=[
            'visit_revenue_amount', 'technician_pool_amount', 'company_share_amount',
            'visit_payout_amount', 'payout_status', 'updated_at',
        ])
        result.payout_status = job.payout_status
        result.reason = 'no_eligible_partner_attendees'
        logger.info('Payout held for job %s: no eligible partner attendees', job.code)
        from core.revenue_audit import log_revenue_event
        log_revenue_event(
            action='payout_held',
            booking_id=job.code or str(job.id),
            details={'reason': result.reason, 'economics': economics, 'pool': str(technician_pool)},
        )
        return result

    amounts = split_pool_equally(technician_pool, len(eligible))
    lead_amount = Decimal('0.00')

    for row, amount in zip(eligible, amounts):
        share_pct = quantize_money(
            (amount / technician_pool * Decimal('100')) if technician_pool else 0
        )
        row.payout_amount_snapshot = amount
        row.share_percent_snapshot = share_pct
        row.save(update_fields=['payout_amount_snapshot', 'share_percent_snapshot', 'updated_at'])

        partner = _resolve_partner_for_row(row)
        partner_id = partner.id if partner else None
        result.participant_payouts.append(
            ParticipantPayout(
                participation_id=row.id,
                technician_id=row.technician_id,
                partner_id=partner_id,
                amount=amount,
                share_percent=share_pct,
            )
        )
        if row.role == JobCardTechnicianParticipation.Role.LEAD or (
            job.technician_id and row.technician_id == job.technician_id
        ):
            lead_amount = amount

        if partner:
            earning, _created = PartnerEarning.objects.update_or_create(
                job=job,
                partner=partner,
                earning_type=PartnerEarning.EarningType.REVENUE_SHARE,
                defaults={
                    'amount': amount,
                    'participation': row,
                    'is_approved': False,
                },
            )
            logger.info(
                'PartnerEarning #%s job=%s partner=%s amount=%s',
                earning.id,
                job.code,
                partner.id,
                amount,
            )

    if lead_amount == 0 and amounts:
        lead_amount = amounts[0]

    job.visit_revenue_amount = visit_revenue
    job.technician_pool_amount = technician_pool
    job.company_share_amount = company_share
    job.visit_payout_amount = lead_amount
    job.payout_status = JobCard.PayoutStatus.PENDING
    job.save(update_fields=[
        'visit_revenue_amount', 'technician_pool_amount', 'company_share_amount',
        'visit_payout_amount', 'payout_status', 'updated_at',
    ])
    result.payout_status = job.payout_status
    from core.revenue_audit import log_revenue_event
    log_revenue_event(
        action='payout_calculated',
        booking_id=job.code or str(job.id),
        details={
            'economics': economics,
            'visit_revenue': str(visit_revenue),
            'technician_pool': str(technician_pool),
            'participants': len(eligible),
            'payout_status': job.payout_status,
        },
    )
    return result


def try_apply_payout_after_completion(job) -> Optional[PayoutResult]:
    """Best-effort wrapper for complete hooks — never raises into callers."""
    try:
        if not is_revenue_model_enabled():
            return None
        return calculate_and_apply_payout(job)
    except Exception:
        logger.exception('Payout engine failed for job %s', getattr(job, 'code', job.pk))
        return None
