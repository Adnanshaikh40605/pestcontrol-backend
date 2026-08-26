"""
Backfill Bed Bugs 2-visit packages on already-created bookings.

Usage:
  python manage.py heal_bed_bug_packages --dry-run
  python manage.py heal_bed_bug_packages
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from core.booking_schedule_engine import heal_all_bed_bug_packages, is_bed_bug_service
from core.models import JobCard
from core.payout_engine import (
    _package_root,
    _tech_share_percent,
    _visit_divisor,
    calculate_and_apply_payout,
    is_bed_bug_multi_visit,
    quantize_money,
    service_line_package_amount,
)


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal('0.00')


def _is_zero_price(job) -> bool:
    raw = str(getattr(job, 'price', '') or '').strip()
    return raw in ('', '0', '0.0', '0.00', '00.00')


def find_prior_bed_bug_package(orphan: JobCard) -> JobCard | None:
    """Nearest earlier Done Bed Bugs package for the same client."""
    qs = (
        JobCard.objects.filter(
            client_id=orphan.client_id,
            status=JobCard.JobStatus.DONE,
            parent_job__isnull=True,
            is_complaint_call=False,
        )
        .exclude(id=orphan.id)
        .filter(
            Q(service_type__icontains='bed')
            | Q(source_service__icontains='bed')
            | Q(visit_type__icontains='BED')
        )
    )
    if orphan.schedule_datetime:
        qs = qs.filter(schedule_datetime__lt=orphan.schedule_datetime)
    else:
        qs = qs.filter(created_at__lt=orphan.created_at)

    candidates = list(qs.order_by('-schedule_datetime', '-id')[:8])
    for prior in candidates:
        # Prefer single-line Bed Bugs packages (not multi-service shells).
        st = (prior.service_type or '')
        if ',' in st and not is_bed_bug_service(st.split(',')[0].strip()):
            # Multi shell is OK only when Bed Bugs is one of the lines and orphan
            # should attach under that shell's Bed Bugs day-1 child instead.
            continue
        planned = max(int(prior.planned_visit_count or 0), int(prior.max_cycle or 0), 2)
        if planned < 2 and not is_bed_bug_service(st):
            continue
        return prior
    # Fallback: any prior Done bed package with planned >= 2
    for prior in candidates:
        planned = max(int(prior.planned_visit_count or 0), int(prior.max_cycle or 0))
        if planned >= 2 or is_bed_bug_service(prior.service_type or ''):
            return prior
    return None


def try_link_orphan_bed_bug_visit(orphan: JobCard, *, dry_run: bool = False) -> dict | None:
    """
    Attach a free-standing Bed Bugs visit (price ~0, no parent) under its package.
    Safe to call from create/heal. Returns detail dict when linked, else None.
    """
    if orphan.parent_job_id or orphan.is_complaint_call:
        return None
    if not (
        is_bed_bug_service(orphan.service_type or '')
        or is_bed_bug_service(orphan.source_service or '')
    ):
        return None
    if ',' in (orphan.service_type or ''):
        return None
    if not _is_zero_price(orphan) and _money(orphan.total_amount) > 0:
        # Priced standalone booking — leave alone.
        return None

    prior = find_prior_bed_bug_package(orphan)
    if prior is None:
        return None

    planned = max(int(prior.planned_visit_count or 0), int(prior.max_cycle or 0), 2)
    if planned < 2:
        planned = 2

    placeholder = (
        JobCard.objects.filter(parent_job=prior, service_cycle=2)
        .exclude(status=JobCard.JobStatus.DONE)
        .exclude(id=orphan.id)
        .order_by('id')
        .first()
    )

    detail = {
        'orphan_id': orphan.id,
        'parent_id': prior.id,
        'placeholder_id': placeholder.id if placeholder else None,
        'cleared_paid': bool((_money(orphan.paid_amount) > 0)),
    }
    if dry_run:
        return detail

    with transaction.atomic():
        if placeholder and placeholder.id != orphan.id:
            placeholder.service_cycle = 900000 + int(placeholder.id)
            placeholder.status = JobCard.JobStatus.CANCELLED
            placeholder.cancellation_reason = (
                (placeholder.cancellation_reason or '')
                + f' | Auto-cancelled: replaced by completed orphan visit #{orphan.id}'
            ).strip(' |')
            placeholder.save(update_fields=[
                'service_cycle', 'status', 'cancellation_reason', 'updated_at',
            ])

        orphan.parent_job = prior
        orphan.service_cycle = 2
        orphan.max_cycle = max(int(orphan.max_cycle or 0), planned, 2)
        orphan.planned_visit_count = orphan.max_cycle
        orphan.is_followup_visit = True
        orphan.is_service_call = True
        orphan.source_service = orphan.source_service or prior.source_service or prior.service_type
        orphan.price = '0'
        orphan.total_amount = Decimal('0.00')
        if _money(orphan.paid_amount) > 0:
            orphan.paid_amount = Decimal('0.00')
            orphan.pending_amount = Decimal('0.00')
        orphan.payment_status = JobCard.PaymentStatus.PAID
        orphan.booking_type = JobCard.BookingType.SERVICE_CALL
        orphan.booking_category = JobCard.BookingCategory.SERVICE_CALL
        if orphan.payout_status in (
            JobCard.PayoutStatus.LEGACY_EXEMPT,
            JobCard.PayoutStatus.NOT_APPLICABLE,
        ):
            orphan.payout_status = JobCard.PayoutStatus.PENDING
        if not orphan.payment_model:
            orphan.payment_model = JobCard.PaymentModel.REVENUE_SHARING
        orphan.save()
        if orphan.status == JobCard.JobStatus.DONE:
            calculate_and_apply_payout(orphan, force=True)
    return detail


def heal_completed_bed_bug_followups() -> tuple[int, int]:
    """Normalize old cycle-2 Bed Bugs rows and force payout recompute."""
    fixed = 0
    recalculated = 0
    qs = JobCard.objects.filter(
        status=JobCard.JobStatus.DONE,
        service_cycle__gte=2,
    ).filter(
        Q(service_type__icontains='bed') | Q(source_service__icontains='bed'),
    )
    from core.booking_schedule_engine import enforce_fixed_service_rules_on_job

    for job in qs.iterator():
        if ',' in (job.service_type or ''):
            continue
        changed = enforce_fixed_service_rules_on_job(job)
        if changed:
            fixed += 1
            job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))
        if job.payout_status in (
            JobCard.PayoutStatus.APPROVED,
            JobCard.PayoutStatus.PAID,
            JobCard.PayoutStatus.CANCELLED,
        ):
            continue
        if job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT:
            job.payout_status = JobCard.PayoutStatus.PENDING
            job.save(update_fields=['payout_status', 'updated_at'])
        result = calculate_and_apply_payout(job, force=True)
        if not result.skipped:
            recalculated += 1
    return fixed, recalculated


def heal_bed_bug_visit_allocations(*, dry_run: bool = False) -> dict:
    """
    Force half-package visit_revenue / 40% tech share on Done Bed Bugs visits
    where amounts are missing or wrong (including legacy_exempt rows).
    Skips locked APPROVED/PAID and multi-service package shells.
    """
    scanned = 0
    fixed = 0
    skipped_locked = 0
    details: list[dict] = []

    qs = JobCard.objects.filter(
        status=JobCard.JobStatus.DONE,
        is_complaint_call=False,
    ).filter(
        Q(service_type__icontains='bed')
        | Q(source_service__icontains='bed')
        | Q(visit_type__icontains='BED'),
    ).exclude(
        payout_status__in=(
            JobCard.PayoutStatus.APPROVED,
            JobCard.PayoutStatus.PAID,
            JobCard.PayoutStatus.CANCELLED,
        ),
    ).select_related('parent_job', 'technician')

    for job in qs.iterator(chunk_size=100):
        st = (job.service_type or '')
        if ',' in st and not job.parent_job_id:
            continue  # multi-service shell — ledger lives on children
        if not is_bed_bug_multi_visit(job) and not is_bed_bug_service(st) and not is_bed_bug_service(
            job.source_service or ''
        ):
            continue

        scanned += 1
        root = _package_root(job)
        pkg = service_line_package_amount(job)
        if pkg <= 0:
            continue
        divisor = max(_visit_divisor(job, root), 2)
        expected_vr = quantize_money(pkg / Decimal(divisor))
        expected_vp = quantize_money(expected_vr * _tech_share_percent(job) / Decimal('100'))
        vr = _money(job.visit_revenue_amount)
        vp = _money(job.visit_payout_amount)

        needs = abs(vr - expected_vr) > Decimal('1.00')
        # Missing tech share when a technician is assigned (held=0 without tech is OK).
        if job.technician_id and abs(vp - expected_vp) > Decimal('1.00') and job.payout_status != JobCard.PayoutStatus.HELD:
            needs = True
        if not needs:
            continue

        detail = {
            'id': job.id,
            'parent_id': job.parent_job_id,
            'from_vr': float(vr),
            'to_vr': float(expected_vr),
            'from_vp': float(vp),
            'to_vp': float(expected_vp),
            'payout_status': job.payout_status,
        }
        details.append(detail)
        if dry_run:
            fixed += 1
            continue

        if job.payout_status in (
            JobCard.PayoutStatus.LEGACY_EXEMPT,
            JobCard.PayoutStatus.NOT_APPLICABLE,
        ):
            job.payout_status = JobCard.PayoutStatus.PENDING
            job.save(update_fields=['payout_status', 'updated_at'])
        if not job.payment_model:
            job.payment_model = JobCard.PaymentModel.REVENUE_SHARING
            job.save(update_fields=['payment_model', 'updated_at'])
        if not job.max_cycle or int(job.max_cycle) < 2:
            job.max_cycle = 2
            job.planned_visit_count = max(int(job.planned_visit_count or 0), 2)
            job.save(update_fields=['max_cycle', 'planned_visit_count', 'updated_at'])

        result = calculate_and_apply_payout(job, force=True)
        if result.skipped and result.reason == 'payout_locked':
            skipped_locked += 1
        else:
            fixed += 1

    return {
        'scanned': scanned,
        'fixed': fixed,
        'skipped_locked': skipped_locked,
        'details': details,
        'dry_run': dry_run,
    }


def heal_bed_bug_followup_duplicate_payments(*, dry_run: bool = False) -> dict:
    """Clear customer payment wrongly stored on included Bed Bugs visit 2+ rows."""
    qs = JobCard.objects.filter(
        parent_job__isnull=False,
        is_complaint_call=False,
        paid_amount__gt=0,
    ).filter(
        Q(service_type__icontains='bed') | Q(source_service__icontains='bed'),
    ).filter(
        Q(service_cycle__gte=2) | Q(price='0') | Q(price='0.0') | Q(price='0.00') | Q(price='00.00') | Q(price=''),
    )

    cleared = 0
    details: list[dict] = []
    for job in qs.iterator():
        if ',' in (job.service_type or ''):
            continue
        detail = {
            'id': job.id,
            'parent_id': job.parent_job_id,
            'paid': float(_money(job.paid_amount)),
        }
        details.append(detail)
        if dry_run:
            cleared += 1
            continue
        job.paid_amount = Decimal('0.00')
        job.pending_amount = Decimal('0.00')
        job.payment_status = JobCard.PaymentStatus.PAID
        job.save(update_fields=['paid_amount', 'pending_amount', 'payment_status', 'updated_at'])
        cleared += 1

    return {'cleared': cleared, 'details': details, 'dry_run': dry_run}


def heal_orphan_bed_bug_second_visits(*, dry_run: bool = False) -> dict:
    """
    Relink Done Bed Bugs rows that were created as separate bookings (price ~0,
    cycle 1, no parent) back under the original package as Service 2.
    """
    orphans = JobCard.objects.filter(
        Q(service_type__icontains='bed') | Q(source_service__icontains='bed'),
        parent_job__isnull=True,
        status=JobCard.JobStatus.DONE,
        is_complaint_call=False,
        service_cycle=1,
    ).filter(
        Q(price='0') | Q(price='0.0') | Q(price='0.00') | Q(price='00.00') | Q(price=''),
    ).select_related('client')

    linked = 0
    cancelled_placeholders = 0
    payment_cleared = 0
    details: list[dict] = []

    for orphan in orphans.iterator():
        detail = try_link_orphan_bed_bug_visit(orphan, dry_run=dry_run)
        if not detail:
            continue
        linked += 1
        if detail.get('placeholder_id'):
            cancelled_placeholders += 1
        if detail.get('cleared_paid'):
            payment_cleared += 1
        details.append(detail)

    return {
        'scanned': orphans.count(),
        'linked': linked,
        'cancelled_placeholders': cancelled_placeholders,
        'payment_cleared': payment_cleared,
        'details': details,
        'dry_run': dry_run,
    }


class Command(BaseCommand):
    help = 'Lock Bed Bugs to 2 visits, link orphans, and fix visit allocation payouts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Count bookings that need healing without writing.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        result = heal_all_bed_bug_packages(dry=dry)
        orphan = heal_orphan_bed_bug_second_visits(dry_run=dry)
        alloc = heal_bed_bug_visit_allocations(dry_run=dry)
        dups = heal_bed_bug_followup_duplicate_payments(dry_run=dry)
        suffix = ' (dry-run)' if dry else ''

        if dry:
            self.stdout.write(self.style.SUCCESS(
                f"packages scanned={result['scanned']} healable={result['healed']} "
                f"missing_visits={result['created_visits']}{suffix} | "
                f"orphan_linkable={orphan['linked']} | "
                f"allocation_fixable={alloc['fixed']} | "
                f"dup_payments_clearable={dups['cleared']}"
            ))
            return

        fixed, recalculated = heal_completed_bed_bug_followups()
        # Re-run allocation after follow-up flag normalize.
        alloc = heal_bed_bug_visit_allocations(dry_run=False)
        self.stdout.write(self.style.SUCCESS(
            f"packages scanned={result['scanned']} healed={result['healed']} "
            f"created_visits={result['created_visits']} | "
            f"followup_flags_fixed={fixed} payouts_recalculated={recalculated} | "
            f"orphan_visit2_linked={orphan['linked']} "
            f"placeholders_cancelled={orphan['cancelled_placeholders']} "
            f"orphan_payments_cleared={orphan['payment_cleared']} | "
            f"allocation_fixed={alloc['fixed']} | "
            f"followup_dup_payments_cleared={dups['cleared']}"
        ))
        for row in orphan['details'][:20]:
            self.stdout.write(
                f"  orphan=#{row['orphan_id']} -> parent=#{row['parent_id']} "
                f"placeholder={row['placeholder_id']} cleared_paid={row['cleared_paid']}"
            )
        for row in alloc['details'][:20]:
            self.stdout.write(
                f"  alloc=#{row['id']} vr {row['from_vr']}→{row['to_vr']} "
                f"vp {row['from_vp']}→{row['to_vp']}"
            )