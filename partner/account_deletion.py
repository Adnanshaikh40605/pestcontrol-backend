"""Permanent partner account deletion (Google Play account-deletion requirement)."""

from __future__ import annotations

import logging
import secrets

from django.db import transaction
from django.utils import timezone

from core.models import JobCard
from partner.models import Partner, PartnerDeviceToken

logger = logging.getLogger(__name__)


class PartnerAccountDeletionError(Exception):
    """User-facing deletion blocked or invalid."""

    def __init__(self, message: str, code: str = 'deletion_not_allowed'):
        self.message = message
        self.code = code
        super().__init__(message)


def _active_job_queryset(partner: Partner):
    return JobCard.objects.filter(
        partner=partner,
        partner_status__in=[
            JobCard.PartnerStatus.ACCEPTED,
            JobCard.PartnerStatus.IN_SERVICE,
        ],
    )


def permanently_delete_partner_account(partner: Partner) -> None:
    """
    Irreversibly close the partner app account: anonymize PII, revoke access,
    remove push tokens. Completed job history is retained for legal/billing records.
    """
    if not partner.is_active and partner.full_name.startswith('Deleted Partner '):
        raise PartnerAccountDeletionError(
            'This account has already been deleted.',
            code='already_deleted',
        )

    if _active_job_queryset(partner).exists():
        raise PartnerAccountDeletionError(
            'You have active accepted or in-progress jobs. Please complete or contact '
            'support before deleting your account.',
            code='active_jobs',
        )

    with transaction.atomic():
        PartnerDeviceToken.objects.filter(partner=partner).delete()

        if partner.profile_image:
            try:
                partner.profile_image.delete(save=False)
            except Exception:
                logger.exception('Failed to delete profile image for partner %s', partner.pk)

        # Release pending broadcast assignments only (not in-progress).
        JobCard.objects.filter(
            partner=partner,
            partner_status=JobCard.PartnerStatus.PENDING,
        ).update(partner=None)

        deleted_at = timezone.now()
        partner.full_name = f'Deleted Partner {partner.pk}'
        # Unique 10-digit placeholder mobile (Indian format).
        partner.mobile = f'9{partner.pk:09d}'[-10:]
        partner.set_password(secrets.token_urlsafe(48))
        partner.bank_name = ''
        partner.account_number = ''
        partner.ifsc_code = ''
        partner.account_holder_name = ''
        partner.profile_image = None
        partner.is_active = False
        partner.is_app_approved = False
        partner.core_technician = None
        partner.save(
            update_fields=[
                'full_name',
                'mobile',
                'password',
                'bank_name',
                'account_number',
                'ifsc_code',
                'account_holder_name',
                'profile_image',
                'is_active',
                'is_app_approved',
                'core_technician',
                'updated_at',
            ]
        )

        logger.info('Partner account %s permanently deleted at %s', partner.pk, deleted_at.isoformat())
