"""
Send a test FCM push to partner app device(s).

Usage:
  python manage.py test_partner_push
  python manage.py test_partner_push --token=DEVICE_FCM_TOKEN
  python manage.py test_partner_push --partner-id=1
"""

from django.core.management.base import BaseCommand

from partner.models import PartnerDeviceToken
from partner.notification_service import active_tokens_for_partners
from partner.push_service import get_fcm_config_status, send_push_to_tokens


class Command(BaseCommand):
    help = 'Send a test new-booking push notification to partner app devices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--token',
            type=str,
            help='Send only to this FCM device token (from partner app login)',
        )
        parser.add_argument(
            '--partner-id',
            type=int,
            help='Send to all active tokens for this partner PK',
        )

    def handle(self, *args, **options):
        status = get_fcm_config_status()
        self.stdout.write(f"FCM status: {status}")

        if not status.get('configured'):
            self.stderr.write(self.style.ERROR('FCM is not configured. Fix Railway env vars first.'))
            return

        token_arg = (options.get('token') or '').strip()
        partner_id = options.get('partner_id')

        if token_arg:
            tokens = [token_arg]
        elif partner_id:
            tokens = list(
                PartnerDeviceToken.objects.filter(
                    partner_id=partner_id, is_active=True
                ).values_list('fcm_token', flat=True)
            )
        else:
            tokens = active_tokens_for_partners()

        if not tokens:
            self.stderr.write(
                self.style.WARNING(
                    'No active FCM tokens. Open the partner app on the phone and log in first.'
                )
            )
            return

        self.stdout.write(f'Sending test push to {len(tokens)} device(s)...')

        result = send_push_to_tokens(
            tokens,
            title='Test — New Booking Available',
            body='Pest 99 test push. If you hear the alert, FCM is working.',
            data={
                'type': 'new_booking',
                'booking_id': '0',
                'job_code': 'TEST',
            },
            collapse_key='test_push',
            channel_id='pest99_new_booking_v2',
            sound='uber_driver_sound',
            data_only=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Done: success={result.get('success', 0)} failure={result.get('failure', 0)}"
        ))
