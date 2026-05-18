"""Partner app booking workflow — shared logic for CRM and partner APIs."""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Q
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
    if not partner.is_app_approved:
        raise PartnerBookingError(
            'Technician partner app is not approved yet. Approve on CRM Technicians page.',
            code='partner_not_approved',
        )
    return partner


def broadcast_pending_filter():
    """Jobs sent to app pool — visible to all approved partners until someone accepts."""
    return Q(
        partner_status=JobCard.PartnerStatus.PENDING,
        sent_to_app_at__isnull=False,
        partner__isnull=True,
    )


@transaction.atomic
def send_booking_to_partner_app(job: JobCard, technician_id=None, sent_by_user=None) -> JobCard:
    """
    CRM: broadcast booking to all approved partner apps (Pending until one accepts).
  technician_id is optional legacy hint only.
    """
    if job.status != JobCard.JobStatus.PENDING:
        raise PartnerBookingError(
            f'Only Pending bookings can be sent to the app (current: {job.status}).',
            code='invalid_status',
        )
    if job.sent_to_app_at and job.partner_status in (
        JobCard.PartnerStatus.PENDING,
        JobCard.PartnerStatus.ACCEPTED,
        JobCard.PartnerStatus.IN_SERVICE,
    ):
        if job.partner_id is None or job.partner_status == JobCard.PartnerStatus.PENDING:
            raise PartnerBookingError(
                'Booking is already in the partner app queue.',
                code='already_sent',
            )

    job.technician = None
    job.assigned_to = ''
    job.partner = None
    job.partner_status = JobCard.PartnerStatus.PENDING
    job.sent_to_app_at = timezone.now()
    job.is_accepted = False
    job.accepted_at = None
    job.started_at = None
    job.job_start_selfie = None
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
        'Booking #%s broadcast to partner app by %s',
        job.id,
        sent_by_user,
    )
    return job


@transaction.atomic
def partner_accept_booking(job: JobCard, partner: Partner) -> JobCard:
    if job.partner_id and job.partner_id != partner.id:
        raise PartnerBookingError('Another technician already accepted this booking.', code='forbidden')

    if job.partner_status != JobCard.PartnerStatus.PENDING:
        raise PartnerBookingError(
            f"Cannot accept booking with status '{job.partner_status}'.",
            code='invalid_state',
        )

    if not job.sent_to_app_at:
        raise PartnerBookingError('Booking was not sent to the partner app.', code='invalid_state')

    tech = partner.core_technician
    if not tech:
        raise PartnerBookingError(
            'Your profile is not linked to a CRM technician record. Contact admin.',
            code='no_technician_link',
        )

    job.partner = partner
    job.technician = tech
    job.assigned_to = tech.name
    job.partner_status = JobCard.PartnerStatus.ACCEPTED
    job.is_accepted = True
    job.accepted_at = timezone.now()
    job.status = JobCard.JobStatus.ON_PROCESS
    job.save(
        update_fields=[
            'partner',
            'technician',
            'assigned_to',
            'partner_status',
            'is_accepted',
            'accepted_at',
            'status',
        ]
    )
    return job


@transaction.atomic
def partner_start_service(job: JobCard, partner: Partner, selfie_file) -> JobCard:
    if job.partner_id != partner.id:
        raise PartnerBookingError('Booking not assigned to you.', code='forbidden')
    if job.partner_status == JobCard.PartnerStatus.IN_SERVICE:
        raise PartnerBookingError('Job already started.', code='already_started')
    if job.partner_status == JobCard.PartnerStatus.COMPLETED:
        raise PartnerBookingError('Job already completed.', code='already_completed')
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
    if job.partner_status == JobCard.PartnerStatus.COMPLETED:
        raise PartnerBookingError('Job already completed.', code='already_completed')
    if job.partner_status == JobCard.PartnerStatus.ACCEPTED:
        raise PartnerBookingError(
            'Start the job with a selfie before ending service.',
            code='not_started',
        )
    if job.partner_status != JobCard.PartnerStatus.IN_SERVICE:
        raise PartnerBookingError(
            'Start the job with a selfie before ending service.',
            code='invalid_state',
        )
    normalized = (payment_mode or '').strip()
    if normalized.lower() == 'cash':
        normalized = JobCard.PaymentMode.CASH
    elif normalized.lower() == 'online':
        normalized = JobCard.PaymentMode.ONLINE
    else:
        raise PartnerBookingError('Payment mode must be Cash or Online.', code='invalid_payment')

    job.partner_status = JobCard.PartnerStatus.COMPLETED
    job.status = JobCard.JobStatus.DONE
    job.payment_mode = normalized
    job.payment_status = JobCard.PaymentStatus.PAID
    job.completed_at = timezone.now()
    if not job.started_at:
        job.started_at = job.completed_at
    job.save(
        update_fields=[
            'partner_status',
            'status',
            'payment_mode',
            'payment_status',
            'completed_at',
            'started_at',
        ]
    )
    return job
