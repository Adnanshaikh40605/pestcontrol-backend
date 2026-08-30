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


def auto_send_new_booking_to_partner_app(job: JobCard, sent_by_user=None) -> bool:
    """
    Idempotent first-time send into the partner app pool.

    Used after CRM create/convert so staff do not need the Action button.
    Returns True only when a new send happened (False for skip / already sent).
    """
    try:
        job.refresh_from_db()
    except JobCard.DoesNotExist:
        return False

    if job.status != JobCard.JobStatus.PENDING:
        return False
    if job.sent_to_app_at:
        return False
    # Follow-ups / complaint calls are not open-pool lineup jobs.
    if job.is_followup_visit or job.is_complaint_call:
        return False
    if job.partner_id is not None:
        return False

    try:
        send_booking_to_partner_app(job, technician_id=None, sent_by_user=sent_by_user)
        return True
    except PartnerBookingError as exc:
        logger.warning(
            'Auto-send to partner app skipped for booking #%s: %s',
            job.id,
            exc.message,
        )
        return False
    except Exception:
        logger.exception('Auto-send to partner app failed for booking #%s', job.id)
        return False


def schedule_auto_send_new_booking_to_partner_app(job: JobCard, sent_by_user=None) -> None:
    """
    Run auto-send after the surrounding DB transaction commits.
    Safe inside nested atomic blocks (inquiry/quotation convert).

    In Django TestCase (always wrapped in a transaction), callers/tests should use
    captureOnCommitCallbacks(execute=True) so the callback runs.
    """
    if not job or not job.pk:
        return

    job_id = job.pk
    user_id = getattr(sent_by_user, 'pk', None)

    def _run():
        from django.contrib.auth import get_user_model

        latest = JobCard.objects.filter(pk=job_id).first()
        if not latest:
            return
        user = None
        if user_id:
            user = get_user_model().objects.filter(pk=user_id).first()
        auto_send_new_booking_to_partner_app(latest, sent_by_user=user)

    # If no atomic block is open, run immediately (management commands, etc.).
    if transaction.get_connection().in_atomic_block:
        transaction.on_commit(_run)
    else:
        _run()


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
    from core.models import Technician
    from partner.presence import ensure_partner_not_suspended, set_partner_presence

    # Lock row so two technicians tapping Accept at the same time cannot both win.
    job = JobCard.objects.select_for_update().get(pk=job.pk)
    ensure_partner_not_suspended(partner)
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
        set_partner_presence(
            partner,
            Technician.PresenceStatus.BUSY,
            allow_system=True,
        )
    except PartnerBookingError:
        pass
    try:
        from core.payout_engine import ensure_lead_participation, is_revenue_model_enabled

        if is_revenue_model_enabled():
            ensure_lead_participation(job)
    except Exception as exc:
        logger.exception('Lead participation sync failed #%s: %s', job.id, exc)
    try:
        from partner.notification_service import notify_crm_booking_accepted

        notify_crm_booking_accepted(job, partner)
    except Exception as exc:
        logger.exception('CRM notify accept failed #%s: %s', job.id, exc)
    return job


@transaction.atomic
def partner_start_service(job: JobCard, partner: Partner, selfie_file) -> JobCard:
    from core.models import Technician
    from partner.presence import ensure_partner_not_suspended, set_partner_presence

    ensure_partner_not_suspended(partner)
    if job.partner_id != partner.id:
        raise PartnerBookingError('Booking not assigned to you.', code='forbidden')
    if job.status == JobCard.JobStatus.CANCELLED:
        raise PartnerBookingError(
            'This booking was already cancelled from CRM.',
            code='cancelled_in_crm',
        )
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
        set_partner_presence(
            partner,
            Technician.PresenceStatus.ON_SERVICE,
            allow_system=True,
        )
    except PartnerBookingError:
        pass
    try:
        from partner.notification_service import notify_crm_service_started

        notify_crm_service_started(job, partner)
    except Exception as exc:
        logger.exception('CRM notify start failed #%s: %s', job.id, exc)
    return job


@transaction.atomic
def partner_complete_booking(job: JobCard, partner: Partner, payment_mode: str) -> JobCard:
    from core.models import Technician
    from partner.presence import set_partner_presence

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

    from core.services import JobCardService

    job.partner_status = JobCard.PartnerStatus.COMPLETED
    job.status = JobCard.JobStatus.DONE
    job.completed_at = timezone.now()
    if not job.started_at:
        job.started_at = job.completed_at
    job.save(
        update_fields=[
            'partner_status',
            'status',
            'completed_at',
            'started_at',
        ]
    )
    # Avoid double-posting if customer (or CRM) already recorded full payment
    already_paid = (job.payment_status or '') == JobCard.PaymentStatus.PAID
    paid_amt = job.paid_amount or 0
    total_amt = job.total_amount or 0
    if not already_paid and not (total_amt and paid_amt and paid_amt >= total_amt):
        JobCardService.apply_completion_payment(
            job,
            user=None,
            payment_mode=normalized,
            collection_type='full',
        )
    elif normalized and job.payment_mode != normalized:
        job.payment_mode = normalized
        job.save(update_fields=['payment_mode', 'updated_at'])
    # Nested atomic = savepoint. IntegrityError / other DB errors inside
    # multi-service sync must not abort the outer complete transaction
    # (status Done + payment already written above).
    try:
        with transaction.atomic():
            from core.payout_engine import try_apply_payout_after_completion
            from core.booking_schedule_engine import (
                BookingScheduleEngine,
                is_multi_service_booking,
            )

            if is_multi_service_booking(job):
                BookingScheduleEngine.sync_multi_service_day1_children(
                    job, completing=True
                )
            try_apply_payout_after_completion(job)
    except Exception as exc:
        logger.exception('Payout after partner complete failed #%s: %s', job.id, exc)
    try:
        set_partner_presence(
            partner,
            Technician.PresenceStatus.ONLINE,
            allow_system=True,
        )
    except PartnerBookingError:
        pass
    try:
        from partner.notification_service import notify_crm_service_completed

        notify_crm_service_completed(job, partner)
    except Exception as exc:
        logger.exception('CRM notify complete failed #%s: %s', job.id, exc)
    return job


def _normalize_area_token(value: str) -> str:
    return ' '.join((value or '').strip().lower().split())


def partner_service_city_tokens(partner: Partner) -> set[str]:
    """City / service-area tokens from the linked CRM technician (legacy text fallback)."""
    tech = getattr(partner, 'core_technician', None)
    tokens: set[str] = set()
    if not tech:
        return tokens
    # Prefer structured service_cities M2M
    for name in tech.service_cities.values_list('name', flat=True):
        token = _normalize_area_token(name)
        if token:
            tokens.add(token)
    if tokens:
        return tokens
    for raw in (tech.city or '', tech.service_area or ''):
        for part in str(raw).replace('/', ',').replace('|', ',').split(','):
            token = _normalize_area_token(part)
            if token:
                tokens.add(token)
    return tokens


def job_matches_partner_service_area(job: JobCard, partner: Partner) -> bool:
    """
    True when the booking city matches the technician service cities.
    Prefer City ID match via M2M; fall back to legacy name tokens.
    If the technician has no city/area configured, allow all (legacy behaviour).
    """
    tech = getattr(partner, 'core_technician', None)
    if tech is not None:
        city_ids = set(tech.service_cities.values_list('id', flat=True))
        if city_ids:
            job_city_id = getattr(job, 'master_city_id', None)
            if job_city_id and job_city_id in city_ids:
                return True
            # Resolve legacy job.city text → master city id when master_city missing
            if not job_city_id and job.city:
                from core.city_utils import resolve_master_city
                resolved = resolve_master_city(job.city)
                if resolved and resolved.id in city_ids:
                    return True
            if job_city_id or job.city:
                return False
            return True  # unscoped job

    allowed = partner_service_city_tokens(partner)
    if not allowed:
        return True

    job_tokens: set[str] = set()
    if job.master_city_id and getattr(job, 'master_city', None):
        job_tokens.add(_normalize_area_token(job.master_city.name))
    if job.city:
        job_tokens.add(_normalize_area_token(job.city))
    if not job_tokens:
        return True  # unscoped jobs remain visible

    for jt in job_tokens:
        for at in allowed:
            if jt == at or jt in at or at in jt:
                return True
    return False


def filter_jobs_today_tomorrow(jobs):
    """Keep only bookings scheduled for today or tomorrow (local date)."""
    today = timezone.localdate()
    tomorrow = today + timezone.timedelta(days=1)
    kept = []
    for job in jobs:
        stamp = job.schedule_datetime
        if not stamp:
            continue
        day = timezone.localtime(stamp).date()
        if day in (today, tomorrow):
            kept.append(job)
    return kept


def apply_partner_pool_filters(jobs, partner: Partner, *, today_tomorrow_only: bool = True):
    """
    City/area filter for partner booking lists.
    Available pool also limits to Today/Tomorrow; accepted work keeps all dates
    so in-progress jobs never disappear from the Accepted tab.
    """
    scoped = [j for j in jobs if job_matches_partner_service_area(j, partner)]
    if today_tomorrow_only:
        return filter_jobs_today_tomorrow(scoped)
    return scoped
