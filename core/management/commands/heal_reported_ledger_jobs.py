"""
Heal the Sep 2026 reported ledger / staff-assignment mismatches.

Fixes both assignment (wrong lead) and stale PartnerEarnings, then rebuilds
payouts so Technician Ledger matches the staff who completed the call.

  python manage.py heal_reported_ledger_jobs
  python manage.py heal_reported_ledger_jobs --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import JobCard, JobCardTechnicianParticipation, Technician
from core.payout_engine import (
    calculate_and_apply_payout,
    ensure_lead_participation,
    enforce_single_lead_participation,
    purge_stale_revenue_share_earnings,
    reassign_job_technician,
    reconcile_job_partner_earnings,
)
from partner.models import PartnerEarning


# Expected lead technician ids (production):
# Akshay=5, Mustafa=2, Mustakim=31, Vaibhav=30, Kuldip=20, Sohil=4
HEALS = [
    # Multi-service shells: move day-1 children onto the correct lead.
    {
        'job_id': 3000,
        'label': 'Saba Khan — children → Akshay',
        'technician_id': 5,
        'move_day1_children': True,
        'force_children': True,  # children currently on Mustafa
    },
    {
        'job_id': 2021,
        'label': 'Sandeep Murdeshwar Society — children → Akshay + Kuldip crew',
        'technician_id': 5,
        'move_day1_children': True,
        'force_children': True,
        'add_crew_ids': [20],  # Kuldip
    },
    # Already correct JobCard.technician; purge stale PartnerEarnings + rebuild.
    {'job_id': 2981, 'label': 'Vivek Verma → Akshay', 'technician_id': 5},
    {'job_id': 3069, 'label': 'Rajeshwari → Mustakim', 'technician_id': 31},
    {'job_id': 2658, 'label': 'Prasad → Mustafa', 'technician_id': 2},
    {'job_id': 2677, 'label': 'Kartik → Mustafa', 'technician_id': 2},
    {'job_id': 3016, 'label': 'Girish Patil → Vaibhav', 'technician_id': 30},
    {'job_id': 2699, 'label': 'Devratan Gupta 2nd service → Vaibhav', 'technician_id': 30},
    {'job_id': 2990, 'label': 'Risa Thattil → Vaibhav', 'technician_id': 30},
    # Pool was split with a bogus second partner; sole lead gets full Tech 40%.
    {'job_id': 3071, 'label': 'Jishnu Das → sole lead ₹480', 'technician_id': 4},
]


class Command(BaseCommand):
    help = 'Heal reported wrong-ledger / technician-amount jobs.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry = options['dry_run']
        for spec in HEALS:
            self._heal_one(spec, dry=dry)

    def _heal_one(self, spec: dict, *, dry: bool) -> None:
        job_id = spec['job_id']
        try:
            job = JobCard.objects.select_related('technician', 'partner').get(pk=job_id)
        except JobCard.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'#{job_id} not found — skip'))
            return

        tech = Technician.objects.get(pk=spec['technician_id'])
        self.stdout.write(
            f"\n#{job_id} {spec['label']}\n"
            f"  current tech={getattr(job.technician, 'name', None)!r} "
            f"→ target={tech.name!r} status={job.status}"
        )

        if dry:
            earns = list(
                PartnerEarning.objects.filter(job=job).values_list(
                    'partner_id', 'amount', 'earning_type'
                )
            )
            kids = list(
                JobCard.objects.filter(parent_job=job, service_cycle=1).values_list(
                    'id', 'technician_id', 'status'
                )
            )
            self.stdout.write(f'  dry-run earns={earns} day1={kids}')
            return

        targets = [job]
        if spec.get('move_day1_children'):
            children = list(
                JobCard.objects.filter(parent_job=job, service_cycle=1).exclude(
                    status=JobCard.JobStatus.CANCELLED
                )
            )
            if spec.get('force_children'):
                targets = children or [job]
            else:
                targets = children + [job]

        for target in targets:
            if target.technician_id != tech.id:
                result = reassign_job_technician(target, tech)
                self.stdout.write(
                    f"  reassigned #{target.id}: "
                    f"{result['previous_technician_name']!r} → {result['technician_name']!r}"
                )
            else:
                ensure_lead_participation(target)
                enforce_single_lead_participation(target)

            for crew_id in spec.get('add_crew_ids') or []:
                crew = Technician.objects.get(pk=crew_id)
                partner = getattr(crew, 'partner_account', None)
                JobCardTechnicianParticipation.objects.update_or_create(
                    jobcard=target,
                    technician=crew,
                    defaults={
                        'partner': partner,
                        'role': JobCardTechnicianParticipation.Role.CREW,
                        'attendance_status': (
                            JobCardTechnicianParticipation.AttendanceStatus.COMPLETED
                            if target.status == JobCard.JobStatus.DONE
                            else JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED
                        ),
                        'is_payout_eligible': True,
                    },
                )
                self.stdout.write(f'  added crew {crew.name!r} on #{target.id}')

            if target.status == JobCard.JobStatus.DONE:
                # Drop any non-crew earnings (e.g. bogus test partner on #3071).
                PartnerEarning.objects.filter(
                    job=target,
                    earning_type=PartnerEarning.EarningType.REVENUE_SHARE,
                ).exclude(
                    partner__core_technician_id__in=list(
                        target.technician_participations.values_list(
                            'technician_id', flat=True
                        )
                    )
                ).delete()
                reconcile_job_partner_earnings(target)
                target.refresh_from_db()
                self.stdout.write(
                    f"  payout #{target.id}: pool={target.technician_pool_amount} "
                    f"lead={target.visit_payout_amount} status={target.payout_status}"
                )

        # Shell packages: hide zero-share shell noise if children carry ledger.
        if spec.get('move_day1_children') and job.status == JobCard.JobStatus.DONE:
            calculate_and_apply_payout(job, force=True)
            purge_stale_revenue_share_earnings(job)
