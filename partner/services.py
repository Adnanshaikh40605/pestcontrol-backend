"""Partner app booking workflow — shared logic for CRM and partner APIs."""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models import JobCard, Technician
from partner.models import Partner

logger = logging.getLogger(__name__)


class PartnerBookingError(Exception):
    """Raised when a partner workflow action is invalid."""

    def __init__(self, message: str, code: str = 'invalid_state'):
        self.message = message
        self.code = code
        super().__init__(message)


def get_partner_for_technician(technician: Technician) -> Partner:
    partner = getattr(technician, 'partner_account', None)
    if not partner or not partner.is_active:
        raise PartnerBookingError(
            'This technician does not have an active Partner App account. '
            'Link or create a partner account first.',
            code='no_partner_account',
        )
    return partner


@transaction.atomic
def send_booking_to_partner_app(job: JobCard, technician_id: int, sent_by_user=None) -> JobCard:
    """
    CRM: assign booking to partner app without moving to On Process.
    Technician must accept in the app first.
    """
    if job.status != JobCard.JobStatus.PENDING:
        raise PartnerBookingError(
            f'Only Pending bookings can be sent to the app (current: {job.status}).',
            code='invalid_status',
        )
    if job.partner_id and job.partner_status in (
        JobCard.PartnerStatus.PENDING,
        JobCard.PartnerStatus.ACCEPTED,
        JobCard.PartnerStatus.IN_SERVICE,
        JobCard.PartnerStatus.COMPLETED,
    ):
        raise PartnerBookingError(
            'Booking is already linked to the partner app.',
            code='already_sent',
        )

    try:
        technician = Technician.objects.select_related('partner_account').get(
            id=technician_id, is_active=True
        )
    except Technician.DoesNotExist:
        raise PartnerBookingError('Technician not found or inactive.', code='not_found')

    partner = get_partner_for_technician(technician)

    job.technician = technician
    job.assigned_to = technician.name
    job.partner = partner
    job.partner_status = JobCard.PartnerStatus.PENDING
    job.sent_to_app_at = timezone.now()
    job.is_accepted = False
    job.accepted_at = None
    job.started_at = None
    job.job_start_selfie = None
    # CRM status stays Pending until partner accepts in the app
    job.save(
        update_fields=[
            'technician',
            'assigned_to',
            'partner',
            'partner_status',
            'sent_to_app_at',
            'is_accepted',
            'accepted_at',
            'started_at',
            'job_start_selfie',
        ]
    )
    logger.info(
        'Booking #%s sent to partner app for %s (partner_id=%s) by %s',
        job.id,
        partner.full_name,
        partner.id,
        sent_by_user,
    )
    return job


@transaction.atomic
def partner_accept_booking(job: JobCard, partner: Partner) -> JobCard:
    if job.partner_id != partner.id:
        raise PartnerBookingError('Booking not assigned to you.', code='forbidden')
    if job.partner_status != JobCard.PartnerStatus.PENDING:
        raise PartnerBookingError(
            f"Cannot accept booking with status '{job.partner_status}'.",
            code='invalid_state',
        )

    job.partner_status = JobCard.PartnerStatus.ACCEPTED
    job.is_accepted = True
    job.accepted_at = timezone.now()
    job.status = JobCard.JobStatus.ON_PROCESS
    job.save(update_fields=['partner_status', 'is_accepted', 'accepted_at', 'status'])
    return job


@transaction.atomic
def partner_start_service(job: JobCard, partner: Partner, selfie_file) -> JobCard:
    if job.partner_id != partner.id:
        raise PartnerBookingError('Booking not assigned to you.', code='forbidden')
    if job.partner_status != JobCard.PartnerStatus.ACCEPTED:
        raise PartnerBookingError(
            f"Can only start an accepted booking (current: '{job.partner_status}').",
            code='invalid_state',
        )
    if not selfie_file:
        raise PartnerBookingError('Selfie image is required to start the job.', code='selfie_required')

    job.job_start_selfie = selfie_file
    job.partner_status = JobCard.PartnerStatus.IN_SERVICE
    job.started_at = timezone.now()
    job.save(update_fields=['job_start_selfie', 'partner_status', 'started_at'])
    return job


@transaction.atomic
def partner_complete_booking(job: JobCard, partner: Partner, payment_mode: str) -> JobCard:
    if job.partner_id != partner.id:
        raise PartnerBookingError('Booking not assigned to you.', code='forbidden')
    if job.partner_status != JobCard.PartnerStatus.IN_SERVICE:
        raise PartnerBookingError(
            'Start the job with a selfie before ending service.',
            code='invalid_state',
        )
    if payment_mode not in ('Cash', 'Online'):
        raise PartnerBookingError('Payment mode must be Cash or Online.', code='invalid_payment')

    job.partner_status = JobCard.PartnerStatus.COMPLETED
    job.status = JobCard.JobStatus.DONE
    job.payment_mode = payment_mode
    job.payment_status = JobCard.PaymentStatus.PAID
    job.completed_at = timezone.now()
    if not job.started_at:
        job.started_at = job.completed_at
    job.save()
    return job
