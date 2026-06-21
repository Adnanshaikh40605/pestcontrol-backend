from django.core.management.base import BaseCommand
from django.utils import timezone

from staff_tracking.models import TrackingSettings
from staff_tracking.operations_models import FieldVisit


class Command(BaseCommand):
    help = 'Mark scheduled visits as missed when check-in grace period has passed.'

    def handle(self, *args, **options):
        settings = TrackingSettings.get_solo()
        now = timezone.now()
        grace = timezone.timedelta(minutes=settings.missed_visit_grace_minutes)
        qs = FieldVisit.objects.filter(
            status=FieldVisit.Status.SCHEDULED,
            scheduled_at__lt=now - grace,
        )
        count = qs.update(status=FieldVisit.Status.MISSED, missed_reason='Auto-flagged: no check-in')
        self.stdout.write(self.style.SUCCESS(f'Marked {count} visit(s) as missed.'))
