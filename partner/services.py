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
        status=JobCard.JobStatus.PENDING,
        partner_status=JobCard.PartnerStatus.PENDING,
        sent_to_app_at__isnull=False,
        partner__isnull=True,
    )


def clear_partner_app_on_crm_cancel(job: JobCard) -> None:
    """Remove a CRM-cancelled booking from the partner app queue (in-memory; caller saves)."""
    job.sent_to_app_at = None
    job.partner = None
    job.technician = None
    job.assigned_to = ''
    job.is_accepted = False
    job.accepted_at = None
    job.started_at = None


@transaction.atomic
def send_booking_to_partner_app(job: JobCard, technician_id=None, sent_by_user=None) -> tuple[JobCard, bool, dict]:
    """
    CRM: broadcast booking to all approved partner apps (Pending until one accepts).
    technician_id is optional legacy hint; omit to notify all approved partners.

    Returns (job, refloated, notify_result) where refloated=True when the booking was already in the
    open pool and in-app notifications were sent again.
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
        in_open_queue = (
            job.partner_id is None
            and job.partner_status == JobCard.PartnerStatus.PENDING
        )
        if in_open_queue:
            # Already in queue — re-notify partners (force bypasses 90s dedupe).
            notify_result: dict = {}
            try:
                from partner.notification_service import notify_partners_new_booking

                notify_result = notify_partners_new_booking(
                    job, technician_id=technician_id, force=True
                )
            except Exception as exc:
                logger.exception('Partner re-notify failed for booking #%s: %s', job.id, exc)
            return job, True, notify_result
        raise PartnerBookingError(
            'Booking is already accepted or in progress in the partner app.',
            code='already_in_progress',
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
    notify_result = {}
    try:
        from partner.notification_service import notify_partners_new_booking

        notify_result = notify_partners_new_booking(job, technician_id=technician_id)
    except Exception as exc:
        logger.exception('Partner notify failed for booking #%s: %s', job.id, exc)
    return job, False, notify_result


def _raise_if_booking_already_taken(job: JobCard, partner: Partner) -> None:
    """First partner to accept wins; others see a clear message."""
    taken_by_other = job.partner_id is not None and job.partner_id != partner.id
    already_locked = job.partner_status in (
        JobCard.PartnerStatus.ACCEPTED,
        JobCard.PartnerStatus.IN_SERVICE,
        JobCard.PartnerStatus.COMPLETED,
    )
    if taken_by_other or (already_locked and job.partner_id != partner.id):
        raise PartnerBookingError(
            'Booking already accepted by another technician.',
            code='already_accepted',
        )


@transaction.atomic
def partner_accept_booking(job: JobCard, partner: Partner) -> JobCard:
    # Lock row so two technicians tapping Accept at the same time cannot both win.
    job = JobCard.objects.select_for_update().get(pk=job.pk)
    _raise_if_booking_already_taken(job, partner)

    if job.status == JobCard.JobStatus.CANCELLED:
        raise PartnerBookingError(
            'This booking was already cancelled from CRM.',
            code='cancelled_in_crm',
        )

    if job.status != JobCard.JobStatus.PENDING:
        raise PartnerBookingError(
            f'Cannot accept booking with CRM status "{job.status}".',
            code='invalid_state',
        )

    if not job.sent_to_app_at:
        raise PartnerBookingError(
            'This booking is no longer available in the app.',
            code='cancelled_in_crm',
        )

    if job.partner_status != JobCard.PartnerStatus.PENDING:
        _raise_if_booking_already_taken(job, partner)
        raise PartnerBookingError(
            f"Cannot accept booking with status '{job.partner_status}'.",
            code='invalid_state',
        )

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
    try:
        from partner.notification_service import notify_crm_booking_accepted

        notify_crm_booking_accepted(job, partner)
    except Exception as exc:
        logger.exception('CRM notify accept failed #%s: %s', job.id, exc)
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

    from core.image_validation import validate_image_upload

    try:
        validate_image_upload(selfie_file)
    except ValueError as exc:
        raise PartnerBookingError(str(exc), code='invalid_selfie') from exc

    job.job_start_selfie = selfie_file
    job.partner_status = JobCard.PartnerStatus.IN_SERVICE
    job.started_at = timezone.now()
    job.save(update_fields=['job_start_selfie', 'partner_status', 'started_at'])
    try:
        from partner.notification_service import notify_crm_service_started

        notify_crm_service_started(job, partner)
    except Exception as exc:
        logger.exception('CRM notify start failed #%s: %s', job.id, exc)
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
    try:
        from partner.notification_service import notify_crm_service_completed

        notify_crm_service_completed(job, partner)
    except Exception as exc:
        logger.exception('CRM notify complete failed #%s: %s', job.id, exc)
    return job
