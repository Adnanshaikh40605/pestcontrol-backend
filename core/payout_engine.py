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


def service_line_package_amount(job) -> Decimal:
    """
    Billable package for THIS service line (not the whole multi-service booking).

    - Standalone / priced child → own amount
    - Follow-up child (price 0) → amount from parent.service_items matching source_service
    - Classic single-service AMC child → full parent package
    - Multi-service package shell → full package (caller should not pay tech on shell)
    """
    from core.payment_utils import parse_jobcard_price

    own_price = parse_jobcard_price(getattr(job, 'price', None))
    own_total = quantize_money(getattr(job, 'total_amount', None) or 0)
    if own_price > 0:
        return own_price
    if own_total > 0 and not job.parent_job_id:
        return own_total

    source = (job.source_service or job.service_type or '').strip()
    root = _package_root(job)
    items = []
    if isinstance(getattr(job, 'service_items', None), list) and job.service_items:
        items = job.service_items
    elif isinstance(getattr(root, 'service_items', None), list):
        items = root.service_items or []

    if source and items:
        for item in items:
            svc = str((item or {}).get('service') or '').strip()
            if svc and svc.lower() == source.lower():
                amt = parse_jobcard_price((item or {}).get('amount'))
                if amt > 0:
                    return amt

    # Single-item child / parent carrying its line in service_items
    if len(items) == 1:
        amt = parse_jobcard_price((items[0] or {}).get('amount'))
        if amt > 0:
            return amt

    # Classic AMC follow-up (price 0, no line items) → parent package total
    if job.parent_job_id:
        return _billable_total(root)
    return _billable_total(job)


def _package_root(job):
    """Root booking that owns package total / visit count for AMC children."""
    root = job
    seen = set()
    while root.parent_job_id and root.parent_job_id not in seen:
        seen.add(root.id)
        root = root.parent_job
    return root


def _visit_divisor(job, root) -> int:
    # Prefer THIS visit's planned count (per-service child), not the multi package max.
    for candidate in (job.planned_visit_count, job.max_cycle):
        if candidate and int(candidate) > 0:
            return int(candidate)
    if job.parent_job_id:
        return 1
    for candidate in (root.planned_visit_count, root.max_cycle):
        if candidate and int(candidate) > 0:
            return int(candidate)
    return 1


def is_amc_economics(job) -> bool:
    from core.booking_schedule_engine import (
        is_amc_plan,
        is_fixed_visit_service,
        is_termite_only_service,
        service_line_names,
    )
    from core.models import JobCard

    # Product rule: Termite-only is always One-Time (never AMC / service-call chain).
    termite_text = ' '.join(
        filter(
            None,
            [
                job.source_service or '',
                job.service_type or '',
                job.visit_type or '',
            ],
        )
    )
    if is_termite_only_service(termite_text) or is_termite_only_service(job.source_service or ''):
        return False

    # Prefer live service_items plans over stale AMC flags (edit One-Time after AMC create).
    items = job.service_items if isinstance(getattr(job, 'service_items', None), list) else []
    if items:
        names = service_line_names(items)
        # Single-line (or this child's single item): trust that line's plan.
        if len(names) == 1 or job.parent_job_id:
            line = items[0] if job.parent_job_id or len(items) == 1 else None
            if line is None and job.source_service:
                for item in items:
                    if str((item or {}).get('service') or '').strip().lower() == (
                        job.source_service or ''
                    ).strip().lower():
                        line = item
                        break
            if line is not None:
                svc = str((line or {}).get('service') or '')
                plan = str((line or {}).get('plan') or (line or {}).get('frequency') or '')
                if is_fixed_visit_service(svc):
                    return False
                return is_amc_plan(plan)

    # Per-service child of a multi-service package: use THIS line's flags only.
    if job.parent_job_id:
        if job.service_category == JobCard.ServiceCategory.AMC:
            return True
        if job.included_in_amc:
            return True
        if job.booking_type in (
            JobCard.BookingType.AMC_MAIN,
            JobCard.BookingType.AMC_FOLLOWUP,
        ):
            return True
        return False

    if job.service_category == JobCard.ServiceCategory.AMC:
        return True
    if job.included_in_amc or job.is_followup_visit or job.is_amc_main_booking:
        return True
    if job.booking_type in (
        JobCard.BookingType.AMC_MAIN,
        JobCard.BookingType.AMC_FOLLOWUP,
    ):
        return True
    return False


def is_bed_bug_multi_visit(job) -> bool:
    """Bed Bugs is always 2 services — settle 40% of (line package ÷ 2) per completed visit."""
    from core.booking_schedule_engine import is_bed_bug_service, service_line_names

    # Prefer the dedicated line name (day-1 / follow-up children set source_service).
    source = (job.source_service or '').strip()
    if source:
        return is_bed_bug_service(source)

    items = getattr(job, 'service_items', None) or []
    if isinstance(items, list) and items:
        names = service_line_names(items)
        if len(names) == 1:
            return is_bed_bug_service(names[0])
        # Multi-service package shell is not itself a Bed Bugs visit.
        if len(names) > 1 and not job.parent_job_id:
            return False

    service_type = (job.service_type or '').strip()
    if service_type:
        # Avoid treating "Termite, Bed Bugs" combined labels as Bed Bugs-only.
        if ',' in service_type or any(
            marker in service_type.lower()
            for marker in ('cockroach', 'termite', 'mosquito', 'rodent', ' ant', '/ ant')
        ):
            if not is_bed_bug_service(service_type):
                return False
            # Combined blob that mentions bed bugs plus other pests → not bed-bug-only.
            other = (
                'cockroach' in service_type.lower()
                or 'termite' in service_type.lower()
                or 'mosquito' in service_type.lower()
                or 'rodent' in service_type.lower()
            )
            if other or ',' in service_type:
                return False
        return is_bed_bug_service(service_type)

    # Last resort: package root labels only when this job has no own service name.
    root = _package_root(job)
    for text in (root.source_service, root.service_type):
        if text and is_bed_bug_service(text) and ',' not in text:
            return True
    return False


def is_multi_service_package_shell(job) -> bool:
    from core.booking_schedule_engine import is_multi_service_package_shell as _shell

    return _shell(job)


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
    """
    Partner-type technicians who attended the visit earn from the 40% pool.

    Salaried staff are always excluded.
    A Partner app login is preferred (for PartnerEarning rows) but NOT required —
    CRM desk-assigned partner technicians still get the visit commission via
    participation.payout_amount_snapshot so the Technician Ledger shows Tech 40%.

    When the job is already Done, desk-assigned crew (attendance=assigned) are
    treated as completed so 40% splits equally across all assigned partner techs.
    """
    from core.models import JobCard, JobCardTechnicianParticipation, Technician

    attended = {
        JobCardTechnicianParticipation.AttendanceStatus.CHECKED_IN,
        JobCardTechnicianParticipation.AttendanceStatus.COMPLETED,
    }
    if job.status == JobCard.JobStatus.DONE:
        attended.add(JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED)

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
        # Partner-type techs earn even without a linked Partner app account.
        if tech.technician_type == Technician.TechnicianType.PARTNER:
            eligible.append(row)
            continue
        # Fallback: any non-salaried tech that already has a partner link on the row.
        if row.partner_id or getattr(tech, 'partner_account', None):
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

    # Multi-service package: ensure day-1 per-service children exist, then never
    # pay 40% on the shell (tech share lives on those children).
    from core.booking_schedule_engine import (
        BookingScheduleEngine,
        is_multi_service_booking,
    )

    if is_multi_service_booking(job) and not job.parent_job_id:
        BookingScheduleEngine.backfill_missing_day1_children(job)
        job.refresh_from_db()
        if is_multi_service_package_shell(job):
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
                skipped=True,
                reason='multi_service_package_shell',
                payout_status=job.payout_status,
            )

    if job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT and not force:
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

    # Blank payment_model on Done jobs → default to revenue sharing when v2 is on.
    if payment_model != JobCard.PaymentModel.REVENUE_SHARING:
        if not payment_model and (is_revenue_model_enabled() or force):
            job.payment_model = JobCard.PaymentModel.REVENUE_SHARING
            job.save(update_fields=['payment_model', 'updated_at'])
            payment_model = job.payment_model
        else:
            return PayoutResult(
                skipped=True,
                reason='payment_model_not_revenue_sharing',
                payout_status=job.payout_status,
            )

    ensure_lead_participation(job)
    job.refresh_from_db()

    tech_pct = _tech_share_percent(job)
    company_pct = _company_share_percent(job)
    root = _package_root(job)
    line_package = service_line_package_amount(job)

    if is_amc_economics(job):
        economics = 'amc'
        package_total = line_package
        divisor = _visit_divisor(job, root)
        visit_revenue = quantize_money(package_total / Decimal(divisor))
    elif is_bed_bug_multi_visit(job):
        # Product rule: Bed Bugs = 2 services → per completed service value = line/2.
        economics = 'amc'
        package_total = line_package
        divisor = max(_visit_divisor(job, root), 2)
        visit_revenue = quantize_money(package_total / Decimal(divisor))
        if not job.planned_visit_count or int(job.planned_visit_count) < 2:
            job.planned_visit_count = 2
            job.save(update_fields=['planned_visit_count', 'updated_at'])
    elif is_contractual_economics(job):
        economics = 'contractual'
        package_total = line_package
        divisor = _visit_divisor(job, root)
        visit_revenue = quantize_money(package_total / Decimal(divisor))
    else:
        economics = 'one_time'
        visit_revenue = line_package

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
    result = None
    try:
        if is_revenue_model_enabled():
            result = calculate_and_apply_payout(job)
    except Exception:
        logger.exception('Payout engine failed for job %s', getattr(job, 'code', job.pk))

    # Accounts booking-cost snapshot (best-effort; does not block completion).
    try:
        from accounts.services.profit import recalculate_booking_cost

        recalculate_booking_cost(job)
    except Exception:
        logger.exception('Accounts cost snapshot failed for job %s', getattr(job, 'code', job.pk))
    return result
