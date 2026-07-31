"""
Auto-suspend partner technicians inactive longer than AUTO_SUSPEND_OFFLINE_DAYS
without an overlapping approved leave request.

  python manage.py auto_suspend_inactive_technicians
  python manage.py auto_suspend_inactive_technicians --dry-run
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Technician
from core.revenue_audit import log_revenue_event
from core.revenue_constants import AUTO_SUSPEND_OFFLINE_DAYS
from partner.models import PartnerLeaveRequest


class Command(BaseCommand):
    help = (
        f'Suspend partner technicians inactive for {AUTO_SUSPEND_OFFLINE_DAYS}+ days '
        'without approved leave.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--days', type=int, default=AUTO_SUSPEND_OFFLINE_DAYS)

    def handle(self, *args, **options):
        days = options['days']
        dry = options['dry_run']
        cutoff = timezone.now() - timedelta(days=days)
        today = timezone.localdate()

        candidates = Technician.objects.filter(
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        ).exclude(
            presence_status=Technician.PresenceStatus.SUSPENDED,
        ).select_related('partner_account')

        suspended = 0
        skipped_leave = 0
        skipped_active = 0

        for tech in candidates:
            # Still active recently → skip
            if tech.last_active and tech.last_active >= cutoff:
                skipped_active += 1
                continue
            # Never seen online and not marked offline → skip (new records)
            if tech.last_active is None and tech.presence_status not in (
                Technician.PresenceStatus.OFFLINE,
                Technician.PresenceStatus.ONLINE,
            ):
                skipped_active += 1
                continue

            partner = getattr(tech, 'partner_account', None)
            if partner and PartnerLeaveRequest.objects.filter(
                partner=partner,
                status=PartnerLeaveRequest.Status.APPROVED,
                start_date__lte=today,
                end_date__gte=cutoff.date(),
            ).exists():
                skipped_leave += 1
                continue

            msg = (
                f'tech#{tech.id} {tech.name} '
                f'(presence={tech.presence_status}, last_active={tech.last_active})'
            )
            if dry:
                self.stdout.write(f'[dry-run] would suspend {msg}')
                suspended += 1
                continue

            tech.presence_status = Technician.PresenceStatus.SUSPENDED
            tech.suspended_at = timezone.now()
            tech.suspend_reason = (
                f'Auto-suspended: inactive for {days}+ days without approved leave.'
            )
            tech.save(update_fields=[
                'presence_status', 'suspended_at', 'suspend_reason', 'updated_at',
            ])
            log_revenue_event(
                action='technician_auto_suspended',
                details={'technician_id': tech.id, 'days': days, 'last_active': str(tech.last_active)},
            )
            suspended += 1
            self.stdout.write(self.style.WARNING(f'Suspended {msg}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. suspended={suspended} skipped_active={skipped_active} '
                f'skipped_on_leave={skipped_leave} dry_run={dry}'
            )
        )
