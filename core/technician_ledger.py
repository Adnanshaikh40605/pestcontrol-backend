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
    Use the scheduled booking date (same as View Bookings).

    Completion date is only a fallback when schedule is missing, so a visit
    closed the next day still shows under the booked day staff expect.
    """
    stamp = job.schedule_datetime or job.completed_at or job.created_at
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


def exclude_package_shells(jobs):
    """Technician ledger shows per-service rows, not the multi-service package shell."""
    from core.booking_schedule_engine import is_multi_service_package_shell

    return [job for job in jobs if not is_multi_service_package_shell(job)]


def apply_ledger_filters(queryset, params):
    date_from = parse_date(params.get('from') or '')
    date_to = parse_date(params.get('to') or '')
    # Mirrors _report_date: booking schedule date, else completion, else created.
    no_schedule = Q(schedule_datetime__isnull=True)
    no_schedule_or_completion = Q(schedule_datetime__isnull=True, completed_at__isnull=True)
    if date_from:
        queryset = queryset.filter(
            Q(schedule_datetime__date__gte=date_from)
            | (no_schedule & Q(completed_at__date__gte=date_from))
            | (no_schedule_or_completion & Q(created_at__date__gte=date_from))
        )
    if date_to:
        queryset = queryset.filter(
            Q(schedule_datetime__date__lte=date_to)
            | (no_schedule & Q(completed_at__date__lte=date_to))
            | (no_schedule_or_completion & Q(created_at__date__lte=date_to))
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


def job_needs_payout_heal(job) -> bool:
    """
    True when a Done booking's stored Tech 40% does not match product rules.
    Used by ledger GET auto-heal and cleanup so wrong positive payouts are fixed,
    not only Held / ₹0 rows.
    """
    from core.booking_schedule_engine import (
        is_multi_service_booking,
        is_multi_service_package_shell,
    )
    from core.models import JobCard
    from core.payout_engine import (
        is_amc_economics,
        is_bed_bug_multi_visit,
        service_line_package_amount,
        quantize_money,
        _visit_divisor,
        _package_root,
    )

    if job.status != JobCard.JobStatus.DONE:
        return False
    if job.payout_status in (
        JobCard.PayoutStatus.APPROVED,
        JobCard.PayoutStatus.PAID,
        JobCard.PayoutStatus.CANCELLED,
    ):
        return False

    # Historical cutover rows stay Old record forever — never auto-migrate on ledger GET.
    if job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT:
        return False

    visit_pay = quantize_money(job.visit_payout_amount)
    visit_rev = quantize_money(job.visit_revenue_amount)
    package = service_line_package_amount(job)

    if not job.payment_model or visit_pay <= 0:
        # Shell packages store 0 on purpose once day-1 children exist.
        if is_multi_service_package_shell(job) and visit_pay <= 0:
            # Still heal if day-1 children are missing payouts.
            kids = list(
                JobCard.objects.filter(parent_job=job, service_cycle=1).exclude(
                    status=JobCard.JobStatus.CANCELLED,
                )
            )
            if not kids:
                return True
            return any(
                (k.status == JobCard.JobStatus.DONE and (k.visit_payout_amount or 0) <= 0)
                for k in kids
            )
        return True

    # Multi-service package paid as one combined row (missing day-1 split).
    if is_multi_service_booking(job) and not job.parent_job_id:
        day1 = JobCard.objects.filter(parent_job=job, service_cycle=1).exclude(
            status=JobCard.JobStatus.CANCELLED,
        ).count()
        if day1 < 2:
            return True
        if visit_pay > 0:
            return True  # shell should be NOT_APPLICABLE with ₹0

    # Bed Bugs: full package in visit_revenue instead of package ÷ 2.
    if is_bed_bug_multi_visit(job) and package > 0:
        expected = quantize_money(package / Decimal('2'))
        if visit_rev >= package and package > expected:
            return True
        full_tech = quantize_money(package * Decimal('0.40'))
        if visit_pay >= full_tech and expected < package:
            return True

    # AMC: full package credited on one visit instead of package ÷ N services.
    if is_amc_economics(job) and package > 0 and not is_bed_bug_multi_visit(job):
        divisor = max(_visit_divisor(job, _package_root(job)), 1)
        if divisor > 1:
            expected_rev = quantize_money(package / Decimal(str(divisor)))
            # Wrong when stored visit revenue is ~full package (or far above per-visit).
            if visit_rev >= package or (
                expected_rev > 0 and visit_rev > expected_rev * Decimal('1.25')
            ):
                return True
            expected_tech = quantize_money(expected_rev * Decimal('0.40'))
            full_tech = quantize_money(package * Decimal('0.40'))
            if visit_pay >= full_tech and expected_tech < full_tech:
                return True

    # Two+ assigned partner techs but only one got the pool (others ₹0).
    parts = list(job.technician_participations.all())
    if len(parts) >= 2 and (job.technician_pool_amount or 0) > 0:
        positive = sum(1 for p in parts if (p.payout_amount_snapshot or 0) > 0)
        eligible_like = sum(
            1 for p in parts
            if p.is_payout_eligible
            and p.attendance_status in (
                'assigned', 'checked_in', 'completed',
            )
        )
        if eligible_like >= 2 and positive < eligible_like:
            return True

    return False


def heal_stuck_payouts(jobs) -> int:
    """
    Recalculate Done jobs with wrong / missing Tech 40% so ledger stays correct.
    Never migrates legacy_exempt history into unsettled payables.
    Handles Bed Bugs ÷2, multi-service day-1 split, and equal 40% across techs.
    """
    from core.booking_schedule_engine import (
        BookingScheduleEngine,
        is_multi_service_booking,
    )
    from core.models import JobCard as JC
    from core.payout_engine import calculate_and_apply_payout

    healed = 0
    for job in jobs:
        if job.payout_status == JC.PayoutStatus.LEGACY_EXEMPT:
            continue
        if not job_needs_payout_heal(job):
            continue
        if is_multi_service_booking(job) and not job.parent_job_id:
            BookingScheduleEngine.sync_multi_service_day1_children(
                job, completing=job.status == JC.JobStatus.DONE,
            )
        result = calculate_and_apply_payout(job, force=True)
        if is_multi_service_booking(job) and not job.parent_job_id:
            for child in JC.objects.filter(
                parent_job=job, service_cycle=1,
            ).exclude(status=JC.JobStatus.CANCELLED):
                if child.status == JC.JobStatus.DONE:
                    calculate_and_apply_payout(child, force=True)
        if not result.skipped or is_multi_service_booking(job):
            healed += 1
            job.refresh_from_db()
    return healed


def serialize_ledger_row(job: JobCard, technician: Technician) -> dict:
    economics = _economics(job)
    completed = job.status == JobCard.JobStatus.DONE
    is_legacy = job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT

    from core.payout_engine import is_bed_bug_multi_visit, service_line_package_amount, _visit_divisor, _package_root

    line_pkg = service_line_package_amount(job)
    planned = job.planned_visit_count or job.max_cycle
    cycle = job.service_cycle or (1 if completed else None)

    # Booking column: per-visit for AMC / Bed Bugs / follow-ups — never the full
    # package total on every visit row (that is what staff call "same charges").
    booking_amount = quantize_money(effective_service_total(job))
    bed_bug_line = is_bed_bug_multi_visit(job)
    if not bed_bug_line:
        primary = (job.source_service or job.service_type or '').strip()
        from core.booking_schedule_engine import is_bed_bug_service

        if primary and is_bed_bug_service(primary) and ',' not in primary:
            bed_bug_line = True

    if bed_bug_line and line_pkg > 0:
        planned_bb = max(int(planned or 0), 2)
        booking_amount = quantize_money(line_pkg / Decimal(planned_bb))
    elif (
        economics in ('amc', 'contract_amc')
        or job.is_followup_visit
        or job.included_in_amc
        or (job.service_cycle or 1) > 1
    ) and line_pkg > 0:
        divisor = max(_visit_divisor(job, _package_root(job)), 1)
        booking_amount = quantize_money(line_pkg / Decimal(divisor))
    elif job.parent_job_id and line_pkg > 0:
        booking_amount = line_pkg

    visit_revenue = Decimal('0.00')
    if completed and not is_legacy:
        visit_revenue = quantize_money(job.visit_revenue_amount)
        # Invent revenue only for real one-time v2 rows with missing snapshots —
        # never for legacy, follow-ups, or multi children that should be ₹0.
        if (
            visit_revenue <= 0
            and economics == 'one_time'
            and not job.is_followup_visit
            and (job.service_cycle or 1) <= 1
            and not job.parent_job_id
        ):
            visit_revenue = booking_amount

    tech_share = Decimal('0.00') if is_legacy else _technician_share(job, technician)
    company_share = (
        Decimal('0.00')
        if is_legacy
        else (quantize_money(job.company_share_amount) if completed else Decimal('0.00'))
    )
    # Prefer stored company share. Only synthesize when payout snapshots exist
    # (visit_revenue was set by the engine) so we don't invent company money
    # on legacy jobs that never ran 40/60.
    if company_share <= 0 and completed and visit_revenue > 0 and (job.technician_pool_amount or 0) > 0:
        company_share = quantize_money(max(visit_revenue - tech_share, Decimal('0.00')))
    bonus, penalty, paid = (Decimal('0.00'), Decimal('0.00'), Decimal('0.00')) if is_legacy else _line_totals(job, technician)
    net = quantize_money(max(tech_share + bonus - penalty, Decimal('0.00')))
    pending = Decimal('0.00') if is_legacy else quantize_money(max(net - paid, Decimal('0.00')))
    feedbacks = list(job.feedbacks.all())
    rating = feedbacks[0].rating if feedbacks else None

    settlement_date = None
    tech_has_paid_share = False
    for line in job.settlement_line_items.all():
        if (
            line.settlement.technician_id == technician.id
            and line.settlement.status == TechnicianSettlement.Status.PAID
            and line.earning_type == SettlementLineItem.EarningType.REVENUE_SHARE
        ):
            tech_has_paid_share = True
            if line.settlement.paid_at:
                settlement_date = timezone.localtime(line.settlement.paid_at).date().isoformat()
            break

    # Per-technician settlement — never treat co-tech PAID as this tech Settled.
    if not completed:
        settlement_status = 'n_a'
        settlement_status_label = 'N/A'
    elif is_legacy:
        settlement_status = 'legacy'
        settlement_status_label = 'Old record'
    elif tech_has_paid_share or (net > 0 and pending <= 0 and paid > 0):
        settlement_status = 'settled'
        settlement_status_label = 'Settled'
        if pending > 0:
            settlement_status = 'unsettled'
            settlement_status_label = 'Unsettled'
    else:
        settlement_status = 'unsettled'
        settlement_status_label = 'Unsettled'

    tech_names = []
    if job.technician_id:
        tech_names.append(job.technician.name if hasattr(job.technician, 'name') else '')
    for part in job.technician_participations.all():
        name = part.technician.name if part.technician_id else ''
        if name and name not in tech_names:
            tech_names.append(name)

    share_pct = job.technician_share_percent or 40
    service_number = None
    booking_type_label = _booking_type_label(economics)

    if bed_bug_line:
        planned = max(int(planned or 0), 2)
        cycle = int(cycle or 1)
        service_number = f'Service {cycle} of {planned}'
        booking_type_label = '2-Service Package'
    # Termite / true one-time must never show "Service 1 of 5" from stale max_cycle.
    elif economics == 'one_time':
        service_number = 'One-Time'
    elif planned and cycle:
        service_number = f'Service {cycle} of {planned}'

    return {
        'job_id': job.id,
        'booking_id': job.code or str(job.id),
        'booking_date': _report_date(job).isoformat(),
        'customer_name': job.client.full_name if job.client_id else '',
        'property_type': job.property_type or job.commercial_type or '',
        'service_type': job.service_type or '',
        'city': job.master_city.name if job.master_city_id else (job.city or ''),
        'booking_type': economics,
        'booking_type_label': booking_type_label,
        'status': job.status,
        'is_completed_visit': completed,
        'service_cycle': cycle,
        'planned_visits': planned,
        'service_number': service_number,
        'assigned_technicians': ', '.join([n for n in tech_names if n]) or '—',
        'technician_share_percent': str(share_pct),
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
        'payout_status_label': settlement_status_label,
        'settlement_status': settlement_status,
        'settlement_status_label': settlement_status_label,
        'settlement_date': settlement_date,
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
        for job in exclude_package_shells(
            technician_jobs_queryset(technician).filter(status=JobCard.JobStatus.DONE)
        )
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
