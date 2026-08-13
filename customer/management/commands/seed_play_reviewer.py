"""Seed Google Play Console reviewer customer account."""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Client
from core.staff_partner_sync import normalize_mobile
from customer.models import CustomerAccount


class Command(BaseCommand):
    help = 'Create / refresh Play Console reviewer customer (fixed OTP mobile).'

    def add_arguments(self, parser):
        parser.add_argument('--mobile', default='9999900999')
        parser.add_argument('--name', default='Play Console Reviewer')

    @transaction.atomic
    def handle(self, *args, **options):
        mobile = normalize_mobile(options['mobile'])
        name = (options['name'] or 'Play Console Reviewer').strip()

        client, _ = Client.objects.get_or_create(
            mobile=mobile,
            defaults={'full_name': name, 'is_active': True},
        )
        if client.full_name != name or not client.is_active:
            client.full_name = name
            client.is_active = True
            client.save(update_fields=['full_name', 'is_active', 'updated_at'])

        account, created = CustomerAccount.objects.get_or_create(
            mobile=mobile,
            defaults={
                'client': client,
                'full_name': name,
                'is_active': True,
            },
        )
        if not created:
            account.client = client
            account.full_name = name
            account.is_active = True
            account.save(update_fields=['client', 'full_name', 'is_active', 'updated_at'])
        else:
            account.set_password(None)
            account.save(update_fields=['password'])

        self.stdout.write(self.style.SUCCESS(
            f'Reviewer ready · mobile={mobile} · account_id={account.id} · created={created}'
        ))
        self.stdout.write(
            'Login: open app → Login → enter mobile → Send OTP → enter CUSTOMER_OTP_REVIEWER_CODE'
        )
