#!/usr/bin/env python3
"""
Fast date-window heal for Technician Ledger + booking flags (production).

Usage (with DATABASE_URL set):
  python scripts/heal_ledger_since.py --since 2026-08-01 --dry-run
  python scripts/heal_ledger_since.py --since 2026-08-01
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, time
from decimal import Decimal

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.booking_schedule_engine import (
    BookingScheduleEngine,
    enforce_fixed_service_rules_on_job,
    heal_bed_bug_package,
    is_multi_service_booking,
    job_includes_bed_bugs,
)
from core.models import JobCard
from core.payment_utils import parse_jobcard_price
from core.payout_engine import calculate_and_apply_payout, service_line_package_amount
from core.technician_ledger import heal_stuck_payouts, job_needs_payout_heal
from partner.models import PartnerEarning

OLD_FOLLOWUP_LEGACY_IDS = {
    390, 1145, 1151, 1176, 1243, 1415, 1576, 1921, 2069, 2159, 2558, 2566,
}


def ids_since(since: date) -> list[int]:
    start = timezone.make_aware(datetime.combine(since, time.min))
    qs = JobCard.objects.filter(
        Q(schedule_datetime__gte=start)
        | Q(completed_at__gte=start)
        | Q(created_at__gte=start)
    ).exclude(status=JobCard.JobStatus.CANCELLED)
    ids = set(qs.values_list('id', flat=True))
    parents = set(
        JobCard.objects.filter(pk__in=ids, parent_job_id__isnull=False)
        .values_list('parent_job_id', flat=True)
    )
    children = set(
        JobCard.objects.filter(parent_job_id__in=ids)
        .exclude(status=JobCard.JobStatus.CANCELLED)
        .values_list('id', flat=True)
    )
    return sorted(ids | parents | children)


def restore_legacy(dry: bool, ids: list[int]) -> int:
    fixed = 0
    for job in JobCard.objects.filter(pk__in=set(ids) & OLD_FOLLOWUP_LEGACY_IDS):
        if (
            job.payout_status == JobCard.PayoutStatus.LEGACY_EXEMPT
            and Decimal(str(job.visit_payout_amount or 0)) <= 0
        ):
            continue
        fixed += 1
        print(f'  legacy #{job.id}', flush=True)
        if dry:
            continue
        job.price = '0'
        job.total_amount = Decimal('0.00')
        job.visit_revenue_amount = Decimal('0.00')
        job.technician_pool_amount = Decimal('0.00')
        job.company_share_amount = Decimal('0.00')
        job.visit_payout_amount = Decimal('0.00')
        job.payout_status = JobCard.PayoutStatus.LEGACY_EXEMPT
        job.is_followup_visit = True
        job.save(update_fields=[
            'price', 'total_amount', 'visit_revenue_amount', 'technician_pool_amount',
            'company_share_amount', 'visit_payout_amount', 'payout_status',
            'is_followup_visit', 'updated_at',
        ])
        PartnerEarning.objects.filter(job=job).delete()
        for part in job.technician_participations.all():
            part.payout_amount_snapshot = Decimal('0.00')
            part.save(update_fields=['payout_amount_snapshot', 'updated_at'])
    return fixed


def heal_multi_lines(dry: bool, ids: list[int]) -> int:
    roots = set()
    for job in JobCard.objects.filter(pk__in=ids).only('id', 'parent_job_id'):
        roots.add(job.parent_job_id or job.id)
    fixed = 0
    for root in JobCard.objects.filter(pk__in=roots, parent_job__isnull=True):
        if not is_multi_service_booking(root):
            continue
        items = root.service_items if isinstance(root.service_items, list) else []
        if len(items) < 2:
            continue
        by_service = {
            str((item or {}).get('service') or '').strip(): parse_jobcard_price((item or {}).get('amount'))
            for item in items
            if str((item or {}).get('service') or '').strip()
        }
        items_sum = sum(by_service.values())
        for child in JobCard.objects.filter(parent_job=root, service_cycle=1).exclude(
            status=JobCard.JobStatus.CANCELLED,
        ):
            key = (child.source_service or child.service_type or '').strip()
            amt = by_service.get(key)
            if amt is None:
                continue
            cur = parse_jobcard_price(child.price)
            tot = Decimal(str(child.total_amount or 0))
            if amt <= 0 and cur > 0 and (items_sum <= 0 or cur < items_sum):
                amt = cur
            full_tech = (items_sum * Decimal('0.40')).quantize(Decimal('0.01')) if items_sum > 0 else Decimal('0')
            line_tech = (amt * Decimal('0.40')).quantize(Decimal('0.01')) if amt > 0 else Decimal('0')
            cur_pay = Decimal(str(child.visit_payout_amount or 0))
            bad = (
                cur != amt
                or tot != amt
                or (items_sum > 0 and cur >= items_sum and len(by_service) > 1)
                or (amt > 0 and Decimal(str(child.visit_revenue_amount or 0)) > amt)
                or (full_tech > 0 and cur_pay >= full_tech and line_tech < full_tech)
            )
            if not bad:
                continue
            fixed += 1
            print(f'  multi-line #{child.id} {key}: {cur}/{tot} → {amt}', flush=True)
            if dry:
                continue
            child.price = str(amt)
            child.total_amount = amt
            child.source_service = key
            child.service_items = [
                item for item in items
                if str((item or {}).get('service') or '').strip() == key
            ] or [{'service': key, 'plan': 'One Time Service', 'area': '', 'amount': float(amt)}]
            if by_service.get(key, Decimal('0')) <= 0 and amt > 0:
                for item in items:
                    if str((item or {}).get('service') or '').strip() == key:
                        item['amount'] = float(amt)
                root.service_items = items
                root.save(update_fields=['service_items', 'updated_at'])
                by_service[key] = amt
            child.save(update_fields=['price', 'total_amount', 'source_service', 'service_items', 'updated_at'])
            if child.status == JobCard.JobStatus.DONE:
                calculate_and_apply_payout(child, force=True)
        if not dry:
            calculate_and_apply_payout(root, force=True)
    return fixed


def cancel_dup_bedbugs(dry: bool, ids: list[int]) -> int:
    roots = set()
    for job in JobCard.objects.filter(pk__in=ids).only('id', 'parent_job_id'):
        roots.add(job.parent_job_id or job.id)
    fixed = 0
    for root_id in roots:
        kids = list(
            JobCard.objects.filter(parent_job_id=root_id, service_cycle=2)
            .exclude(status=JobCard.JobStatus.CANCELLED)
            .order_by('id')
        )
        if len(kids) < 2:
            continue
        keep = next((k for k in kids if k.status == JobCard.JobStatus.DONE), kids[0])
        for kid in kids:
            if kid.id == keep.id:
                continue
            fixed += 1
            print(f'  dup-cancel #{kid.id} keep #{keep.id}', flush=True)
            if dry:
                continue
            kid.status = JobCard.JobStatus.CANCELLED
            kid.visit_revenue_amount = Decimal('0.00')
            kid.technician_pool_amount = Decimal('0.00')
            kid.company_share_amount = Decimal('0.00')
            kid.visit_payout_amount = Decimal('0.00')
            kid.payout_status = JobCard.PayoutStatus.CANCELLED
            kid.save(update_fields=[
                'status', 'visit_revenue_amount', 'technician_pool_amount',
                'company_share_amount', 'visit_payout_amount', 'payout_status', 'updated_at',
            ])
    return fixed


def zero_complaints(dry: bool, ids: list[int]) -> int:
    fixed = 0
    for job in JobCard.objects.filter(pk__in=ids):
        if not (job.is_complaint_call or job.booking_type == JobCard.BookingType.COMPLAINT_CALL):
            continue
        if job.payout_status == JobCard.PayoutStatus.NOT_APPLICABLE and Decimal(str(job.visit_payout_amount or 0)) <= 0:
            continue
        fixed += 1
        print(f'  complaint-zero #{job.id}', flush=True)
        if not dry:
            calculate_and_apply_payout(job, force=True)
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--since', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument(
        '--pass-only',
        choices=('stuck', 'multi', 'all'),
        default='all',
        help='stuck=recalc payouts only; multi=multi-service lines only; all=full sweep',
    )
    parser.add_argument('--batch-size', type=int, default=25)
    args = parser.parse_args()
    since = parse_date(args.since)
    if not since:
        print('Invalid --since', file=sys.stderr)
        return 2
    dry = args.dry_run
    ids = ids_since(since)
    print(f'Since {since}: {len(ids)} IDs pass={args.pass_only}', flush=True)

    if args.pass_only == 'stuck':
        done = list(
            JobCard.objects.filter(pk__in=ids, status=JobCard.JobStatus.DONE)
            .exclude(payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT)
            .exclude(pk__in=OLD_FOLLOWUP_LEGACY_IDS)
            .order_by('id')
        )
        need = [j for j in done if job_needs_payout_heal(j)]
        print(f'  stuck-candidates={len(need)}/{len(done)}', flush=True)
        stuck = 0
        if not dry:
            for i in range(0, len(need), args.batch_size):
                batch = need[i:i + args.batch_size]
                print(f'  stuck-batch {i // args.batch_size + 1} size={len(batch)}', flush=True)
                from django.db import close_old_connections
                close_old_connections()
                stuck += heal_stuck_payouts(batch)
        print(f'DONE stuck={stuck}' + (' (dry-run)' if dry else ''), flush=True)
        return 0

    if args.pass_only == 'multi':
        legacy = restore_legacy(dry, ids)
        multi_lines = heal_multi_lines(dry, ids)
        dups = cancel_dup_bedbugs(dry, ids)
        multi = 0
        for job in JobCard.objects.filter(pk__in=ids, parent_job__isnull=True, status=JobCard.JobStatus.DONE):
            if not is_multi_service_booking(job):
                continue
            multi += 1
            print(f'  multi-sync #{job.id}', flush=True)
            if dry:
                continue
            from django.db import close_old_connections
            close_old_connections()
            BookingScheduleEngine.sync_multi_service_day1_children(job, completing=True)
            calculate_and_apply_payout(job, force=True)
            for child in JobCard.objects.filter(parent_job=job, service_cycle=1).exclude(
                status=JobCard.JobStatus.CANCELLED,
            ):
                if child.status == JobCard.JobStatus.DONE and child.id not in OLD_FOLLOWUP_LEGACY_IDS:
                    calculate_and_apply_payout(child, force=True)
        print(
            f'DONE legacy={legacy} multi_lines={multi_lines} dups={dups} multi={multi}'
            + (' (dry-run)' if dry else ''),
            flush=True,
        )
        return 0

    flags = 0
    bed = 0
    # Only heal Bed Bugs packages that are roots in the window and missing visit 2.
    for job in JobCard.objects.filter(pk__in=ids, parent_job__isnull=True).iterator():
        if not job_includes_bed_bugs(job) or is_multi_service_booking(job):
            continue
        has_second = JobCard.objects.filter(
            parent_job=job, service_cycle=2,
        ).exclude(status=JobCard.JobStatus.CANCELLED).exists()
        need = (job.max_cycle or 0) != 2 or (job.planned_visit_count or 0) != 2 or (
            bool(job.schedule_datetime) and not has_second
        )
        if not need:
            continue
        bed += 1
        print(f'  bedbug-package #{job.id}', flush=True)
        if not dry:
            heal_bed_bug_package(job)

    for job in JobCard.objects.filter(pk__in=ids).iterator():
        changed = enforce_fixed_service_rules_on_job(job)
        if not changed:
            continue
        flags += 1
        if flags <= 50 or flags % 25 == 0:
            print(f'  flags #{job.id}: {changed}', flush=True)
        if not dry:
            job.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))

    legacy = restore_legacy(dry, ids)
    multi_lines = heal_multi_lines(dry, ids)
    dups = cancel_dup_bedbugs(dry, ids)
    complaints = zero_complaints(dry, ids)

    # Multi shells: ensure day-1 children, then recalc.
    multi = 0
    for job in JobCard.objects.filter(pk__in=ids, parent_job__isnull=True, status=JobCard.JobStatus.DONE):
        if not is_multi_service_booking(job):
            continue
        multi += 1
        print(f'  multi-sync #{job.id}', flush=True)
        if dry:
            continue
        BookingScheduleEngine.sync_multi_service_day1_children(job, completing=True)
        calculate_and_apply_payout(job, force=True)
        for child in JobCard.objects.filter(parent_job=job, service_cycle=1).exclude(
            status=JobCard.JobStatus.CANCELLED,
        ):
            if child.status == JobCard.JobStatus.DONE and child.id not in OLD_FOLLOWUP_LEGACY_IDS:
                calculate_and_apply_payout(child, force=True)

    done = list(
        JobCard.objects.filter(pk__in=ids, status=JobCard.JobStatus.DONE)
        .exclude(payout_status=JobCard.PayoutStatus.LEGACY_EXEMPT)
        .exclude(pk__in=OLD_FOLLOWUP_LEGACY_IDS)
        .order_by('id')
    )
    need = [j for j in done if job_needs_payout_heal(j)]
    print(f'  stuck-candidates={len(need)}/{len(done)}', flush=True)
    stuck = 0
    if not dry and need:
        batch = 25
        for i in range(0, len(need), batch):
            chunk = need[i:i + batch]
            healed = heal_stuck_payouts(chunk)
            stuck += healed
            print(f'  stuck-batch {i // batch + 1}: healed={healed}', flush=True)
            # Close stale connections between batches (Railway PG timeout).
            from django.db import connection
            connection.close()

    print(
        f'DONE flags={flags} bedbug={bed} legacy={legacy} multi_lines={multi_lines} '
        f'dups={dups} complaints={complaints} multi={multi} stuck={stuck}'
        + (' (dry-run)' if dry else ''),
        flush=True,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
