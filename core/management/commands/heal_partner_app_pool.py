"""Heal Pending bookings missing from the Partner App open pool."""

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from core.models import JobCard
from partner.services import auto_send_new_booking_to_partner_app


class Command(BaseCommand):
    help = (
        'Set sent_to_app_at for Pending unassigned bookings that never entered '
        'the Partner App pool (common for older customer-app creates).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report bookings that would be healed.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='Max bookings to process (default 500).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        qs = (
            JobCard.objects.filter(
                status=JobCard.JobStatus.PENDING,
                partner__isnull=True,
                sent_to_app_at__isnull=True,
                is_followup_visit=False,
                is_complaint_call=False,
            )
            .filter(
                Q(partner_status='')
                | Q(partner_status__isnull=True)
                | Q(partner_status=JobCard.PartnerStatus.PENDING)
            )
            .order_by('-id')[:limit]
        )
        jobs = list(qs)
        self.stdout.write(f'Found {len(jobs)} Pending booking(s) missing from partner pool.')

        healed = 0
        skipped = 0
        for job in jobs:
            if dry_run:
                self.stdout.write(
                    f'  would heal #{job.id} source={job.creation_source} '
                    f'status={job.status} partner_status={job.partner_status!r}'
                )
                healed += 1
                continue
            ok = auto_send_new_booking_to_partner_app(job, sent_by_user=None)
            if ok:
                healed += 1
                self.stdout.write(self.style.SUCCESS(f'  healed #{job.id}'))
            else:
                skipped += 1
                self.stdout.write(self.style.WARNING(f'  skipped #{job.id}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Done at {timezone.now().isoformat()} — healed={healed} skipped={skipped} dry_run={dry_run}'
            )
        )
