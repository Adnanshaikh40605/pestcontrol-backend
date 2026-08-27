"""Customer booking / rating domain logic."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from core.models import Feedback, JobCard, PricingRate
from core.services import JobCardService

from .models import CustomerAccount

logger = logging.getLogger(__name__)


class CustomerAppError(Exception):
    def __init__(self, message: str, code: str = 'invalid'):
        self.message = message
        self.code = code
        super().__init__(message)


@transaction.atomic
def create_customer_booking(account: CustomerAccount, data: dict) -> JobCard:
    amount = data.get('amount')
    rate = None
    rate_id = data.get('pricing_rate_id')
    if rate_id:
        try:
            rate = PricingRate.objects.select_related('region').get(id=rate_id, is_active=True)
        except PricingRate.DoesNotExist as exc:
            raise CustomerAppError('Pricing rate not found.', code='invalid_rate') from exc
        amount = rate.amount
        if not data.get('service_type'):
            data = {**data, 'service_type': rate.service_package}

    if amount is None:
        raise CustomerAppError('amount or pricing_rate_id is required.', code='amount_required')

    service_type = (data.get('service_type') or '').strip()
    if not service_type and rate:
        service_type = rate.service_package
    if not service_type:
        raise CustomerAppError('service_type is required.', code='service_required')
    data = {**data, 'service_type': service_type}

    amount = Decimal(str(amount))
    package_tier = data.get('package_tier') or JobCard.PackageTier.STANDARD
    if package_tier == JobCard.PackageTier.PREMIUM:
        amount = (amount * Decimal('1.15')).quantize(Decimal('0.01'))

    booking_kind = (data.get('booking_type') or 'one_time').lower()
    service_category = (
        JobCard.ServiceCategory.AMC
        if booking_kind == 'amc'
        else JobCard.ServiceCategory.ONE_TIME
    )

    address = (data.get('address') or '').strip()
    area = (data.get('area') or '').strip()
    if area and area.lower() not in address.lower():
        address = f'{address}, {area}'.strip(', ')

    from core.city_utils import canonical_city_label, resolve_master_city

    raw_city = (data.get('city') or getattr(account.client, 'city', None) or '').strip()
    master_city = resolve_master_city(raw_city)
    city_label = (
        canonical_city_label(master_city.name if master_city else raw_city)
        or raw_city
    )

    # Contractual = society/commercial crew jobs (revenue sharing when flag on).
    if booking_kind == 'contractual':
        job_type = JobCard.JobType.SOCIETY
        commercial_type = JobCard.CommercialType.SOCIETY
        property_type = data.get('property_type') or JobCard.PropertyType.SOCIETY
        contract_duration = data.get('contract_duration') or JobCard.ContractDuration.TWELVE_MONTHS
    else:
        job_type = JobCard.JobType.CUSTOMER
        commercial_type = JobCard.CommercialType.HOME
        property_type = data.get('property_type') or JobCard.PropertyType.HOME_FLAT
        contract_duration = data.get('contract_duration') or ''

    payload = {
        'client': account.client_id,
        'service_type': data.get('service_type') or (rate.service_package if rate else 'General Pest'),
        'service_category': service_category,
        'property_type': property_type,
        'bhk_size': data.get('bhk_size') or '',
        'client_address': address,
        'city': city_label,
        'schedule_datetime': data.get('schedule_datetime'),
        'time_slot': data.get('time_slot') or '',
        'notes': data.get('notes') or '',
        'price': str(amount),
        'total_amount': amount,
        'status': JobCard.JobStatus.PENDING,
        'payment_status': JobCard.PaymentStatus.UNPAID,
        'package_tier': package_tier,
        'reference': 'Customer App',
        'job_type': job_type,
        'commercial_type': commercial_type,
    }
    if master_city:
        payload['master_city'] = master_city.id
    if contract_duration:
        payload['contract_duration'] = contract_duration
    if booking_kind == 'amc':
        # Termite / Bed Bugs never use AMC visit packages from the customer app.
        from core.booking_schedule_engine import is_fixed_visit_service

        service_name = payload.get('service_type') or ''
        if is_fixed_visit_service(service_name):
            payload['service_category'] = JobCard.ServiceCategory.ONE_TIME
            if 'termite' in service_name.lower():
                payload['max_cycle'] = 1
                payload['planned_visit_count'] = 1
            else:
                payload['max_cycle'] = 2
                payload['planned_visit_count'] = 2
            payload['service_cycle'] = 1
        else:
            payload['service_cycle'] = 1
            payload['max_cycle'] = 3

    if getattr(settings, 'REVENUE_MODEL_V2', False):
        payload['payment_model'] = JobCard.PaymentModel.REVENUE_SHARING
        payload['payout_status'] = JobCard.PayoutStatus.NOT_APPLICABLE

    try:
        job = JobCardService.create_jobcard(payload, user=None)
    except Exception as exc:
        logger.exception('Customer booking create failed: %s', exc)
        raise CustomerAppError(str(exc), code='create_failed') from exc

    job.creation_source = JobCard.CreationSource.CUSTOMER_APP
    job.package_tier = package_tier
    job.save(update_fields=['creation_source', 'package_tier', 'updated_at'])

    # Always push into the Partner App open pool (CRM Action not required).
    try:
        from partner.services import schedule_auto_send_new_booking_to_partner_app

        schedule_auto_send_new_booking_to_partner_app(job, sent_by_user=None)
    except Exception:
        logger.exception(
            'Failed to schedule partner-app auto-send for customer booking #%s',
            job.id,
        )

    # Persist last service address on CRM client for future bookings.
    client = account.client
    if client and address:
        updates = []
        if address and client.address != address:
            client.address = address
            updates.append('address')
        city = (data.get('city') or '').strip()
        if city and getattr(client, 'city', None) != city:
            if hasattr(client, 'city'):
                client.city = city
                updates.append('city')
        if updates:
            updates.append('updated_at')
            client.save(update_fields=updates)

    return job


@transaction.atomic
def confirm_customer_payment(account: CustomerAccount, job: JobCard, payment_reference: str = '') -> JobCard:
    if not getattr(settings, 'CUSTOMER_ONLINE_PAYMENT_ENABLED', False):
        raise CustomerAppError(
            'Online payment is not available yet. Please pay after service.',
            code='payment_disabled',
        )
    if job.client_id != account.client_id:
        raise CustomerAppError('Booking not found.', code='forbidden')
    if job.status == JobCard.JobStatus.CANCELLED:
        raise CustomerAppError('Booking is cancelled.', code='cancelled')

    # Idempotent: already fully paid → no second ledger row
    already_paid = (job.payment_status or '') in (
        JobCard.PaymentStatus.PAID,
        getattr(JobCard.PaymentStatus, 'PAID', 'Paid'),
    )
    paid_amt = job.paid_amount or 0
    total_amt = job.total_amount or 0
    if already_paid or (total_amt and paid_amt and paid_amt >= total_amt):
        return job

    JobCardService.apply_completion_payment(
        job,
        user=None,
        payment_mode=JobCard.PaymentMode.ONLINE,
        collection_type='full',
        remarks=f'Customer app payment. Ref: {payment_reference or "n/a"}',
    )
    job.refresh_from_db()
    return job


@transaction.atomic
def create_customer_complaint(account: CustomerAccount, data: dict) -> JobCard:
    note = (data.get('note') or '').strip()
    complaint_type = (data.get('complaint_type') or '').strip()
    if len(note) < 5:
        raise CustomerAppError('Please describe the issue.', code='note_required')
    if not complaint_type:
        raise CustomerAppError('Complaint type is required.', code='type_required')

    parent = None
    booking_id = data.get('booking_id')
    if booking_id:
        try:
            parent = JobCard.objects.select_related('parent_job', 'client').get(
                id=booking_id, client=account.client,
            )
        except JobCard.DoesNotExist as exc:
            raise CustomerAppError('Booking not found.', code='booking_not_found') from exc

    from core.complaint_service import create_complaint_jobcard

    if parent is None:
        # Standalone complaint without a parent booking — still one free service only.
        from core.complaint_service import apply_complaint_constraints

        job = JobCard(
            client=account.client,
            service_type='Complaint / Re-Service',
            client_address=account.client.address or '',
            city=getattr(account.client, 'city', '') or '',
            notes=note,
            status=JobCard.JobStatus.PENDING,
            property_type=JobCard.PropertyType.HOME_FLAT,
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
            creation_source='customer_app',
            complaint_type=complaint_type,
            complaint_note=note,
        )
        apply_complaint_constraints(job, parent=None)
        job.save()
        return job

    return create_complaint_jobcard(
        parent=parent,
        complaint_type=complaint_type,
        complaint_note=note,
        creation_source='customer_app',
    )


@transaction.atomic
def rate_customer_booking(account: CustomerAccount, job: JobCard, data: dict) -> Feedback:
    if job.client_id != account.client_id:
        raise CustomerAppError('Booking not found.', code='forbidden')
    if job.status != JobCard.JobStatus.DONE:
        raise CustomerAppError('You can only rate completed services.', code='not_completed')
    if Feedback.objects.filter(booking=job, rating__gt=0).exists():
        raise CustomerAppError('This booking was already rated.', code='already_rated')

    feedback, _ = Feedback.objects.get_or_create(
        booking=job,
        defaults={'feedback_type': 'Customer App', 'rating': 0},
    )
    feedback.rating = int(data['rating'])
    feedback.remark = data.get('remark') or ''
    feedback.technician_behavior = data.get('technician_behavior') or 'good'
    feedback.feedback_type = 'Customer App'
    feedback.save()
    return feedback


def customer_amc_schedule(account: CustomerAccount):
    qs = JobCard.objects.filter(client=account.client).order_by('-created_at')
    parents = []
    for job in qs:
        bt = (job.booking_type or '').lower()
        is_amc = job.is_amc_main_booking or 'amc' in bt or job.service_category == JobCard.ServiceCategory.AMC
        if not is_amc or job.parent_job_id:
            continue
        children = list(
            JobCard.objects.filter(parent_job=job).order_by('service_cycle', 'schedule_datetime')
        )
        parents.append((job, children))
    return parents
