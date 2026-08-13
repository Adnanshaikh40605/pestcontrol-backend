"""Permanent customer account deletion (Google Play account-deletion requirement)."""

from __future__ import annotations

import logging
import secrets

from django.db import transaction
from django.utils import timezone

from core.models import JobCard
from customer.models import CustomerAccount, CustomerOTPChallenge

logger = logging.getLogger(__name__)


class CustomerAccountDeletionError(Exception):
    def __init__(self, message: str, code: str = 'deletion_not_allowed'):
        self.message = message
        self.code = code
        super().__init__(message)


def permanently_delete_customer_account(account: CustomerAccount) -> None:
    """
    Close the customer app account: anonymize PII, deactivate login.
    Historical JobCards are retained for legal/billing (client link kept, PII scrubbed).
    """
    if not account.is_active and (account.full_name or '').startswith('Deleted Customer '):
        raise CustomerAccountDeletionError(
            'This account has already been deleted.',
            code='already_deleted',
        )

    active = JobCard.objects.filter(
        client=account.client,
        status__in=[
            JobCard.JobStatus.PENDING,
            JobCard.JobStatus.UPCOMING,
            JobCard.JobStatus.ON_PROCESS,
        ],
    ).exists()
    if active:
        raise CustomerAccountDeletionError(
            'You have an active booking. Please wait until it is completed or contact support.',
            code='active_bookings',
        )

    with transaction.atomic():
        deleted_at = timezone.now()
        client = account.client
        pk = account.pk

        CustomerOTPChallenge.objects.filter(mobile=account.mobile).delete()

        account.full_name = f'Deleted Customer {pk}'
        account.mobile = f'8{pk:09d}'[-10:]
        account.email = ''
        account.set_password(secrets.token_urlsafe(48))
        account.is_active = False
        account.save(update_fields=['full_name', 'mobile', 'email', 'password', 'is_active', 'updated_at'])

        if client:
            client.full_name = f'Deleted Customer {pk}'
            client.mobile = account.mobile
            client.email = ''
            client.address = ''
            client.is_active = False
            client.save(update_fields=['full_name', 'mobile', 'email', 'address', 'is_active', 'updated_at'])

        logger.info('Customer account %s permanently deleted at %s', pk, deleted_at.isoformat())
