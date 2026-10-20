"""Business logic for DeepCleaning99 website booking inquiries."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    DeepCleaningBooking,
    DeepCleaningInquiry,
    DeepCleaningInquiryRemark,
    DeepCleaningTechnician,
    RemarkType,
)


class DeepCleaningInquiryService:
    """Create DeepCleaning99 leads without touching pest Inquiry tables."""

    PLACEHOLDER_NAME = 'Website Lead'
    AUTO_NOTE = 'Auto-captured from DeepCleaning99 booking form.'
    DEFAULT_SERVICE = 'Deep Cleaning'

    @staticmethod
    def _normalize_mobile(raw) -> str:
        digits = re.sub(r'\D', '', str(raw or ''))
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        if len(digits) == 11 and digits.startswith('0'):
            digits = digits[1:]
        return digits

    @staticmethod
    def _sanitize_name(raw) -> str:
        text = str(raw or '')
        cleaned = ''.join(
            ch for ch in text
            if ch.isspace() or unicodedata.category(ch).startswith('L')
        ).strip()
        return cleaned[:255]

    @staticmethod
    def _money(raw) -> Decimal | None:
        if raw in (None, ''):
            return None
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError, TypeError):
            return None
        if value < 0:
            return None
        return value.quantize(Decimal('0.01'))

    @classmethod
    def normalize_payload(cls, data: dict[str, Any]) -> dict[str, Any]:
        mobile = cls._normalize_mobile(data.get('mobile'))
        if len(mobile) != 10 or mobile[0] not in '6789':
            raise ValidationError('Enter a valid 10-digit Indian mobile number.')

        name = cls._sanitize_name(data.get('name'))
        if len(name) < 2:
            raise ValidationError('Name is required.')

        service = str(data.get('service') or '').strip()
        if not service:
            raise ValidationError('Service is required.')

        preferred_date = data.get('preferred_date')
        if isinstance(preferred_date, str):
            preferred_date = parse_date(preferred_date.strip()) or None

        plan = str(data.get('plan') or 'one').strip().lower()
        if plan not in ('one', 'amc', 'one-time', 'one_time'):
            plan = 'one'
        if plan in ('one-time', 'one_time'):
            plan = 'one'

        page_url = str(data.get('page_url') or '').strip() or None
        if page_url and len(page_url) > 500:
            page_url = page_url[:500]

        return {
            'name': name,
            'mobile': mobile,
            'email': str(data.get('email') or '').strip() or None,
            'city': str(data.get('city') or 'Mumbai').strip()[:100] or 'Mumbai',
            'area': str(data.get('area') or '').strip()[:150],
            'address': str(data.get('address') or '').strip()[:1000],
            'segment': str(data.get('segment') or 'Residential').strip()[:50] or 'Residential',
            'service': service[:255],
            'package_name': str(data.get('package_name') or data.get('package') or '').strip()[:255],
            'package_id': str(data.get('package_id') or '').strip()[:50],
            'quantity': str(data.get('quantity') or '').strip()[:50],
            'unit': str(data.get('unit') or '').strip()[:50],
            'plan': plan[:50],
            'property_size': str(data.get('property_size') or '').strip()[:50],
            'property_type': str(data.get('property_type') or '').strip()[:50],
            'preferred_date': preferred_date,
            'preferred_time': str(data.get('preferred_time') or data.get('time') or '').strip()[:100],
            'estimated_price': cls._money(data.get('estimated_price')),
            'regular_price': cls._money(data.get('regular_price')),
            'discount_amount': cls._money(data.get('discount_amount')),
            'notes': str(data.get('notes') or data.get('message') or '').strip()[:2000],
            'page_url': page_url,
            'source': 'deepcleaning99',
            'status': DeepCleaningInquiry.InquiryStatus.NEW,
            'is_read': False,
        }

    @classmethod
    def create_inquiry(cls, data: dict[str, Any], user=None) -> DeepCleaningInquiry:
        fields = cls.normalize_payload(data)
        session_id = str(data.get('booking_session_id') or '').strip()
        if session_id:
            fields['booking_session_id'] = session_id[:64]
        inquiry = DeepCleaningInquiry(created_by=user, **fields)
        inquiry.full_clean()
        inquiry.save()
        cls._notify(inquiry)
        return inquiry

    @classmethod
    def _is_placeholder_name(cls, name) -> bool:
        cleaned = (name or '').strip()
        if not cleaned:
            return True
        return cleaned.casefold() == cls.PLACEHOLDER_NAME.casefold()

    @classmethod
    def normalize_capture_payload(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Mobile-only silent capture. Name and service can be filled in later."""
        import re

        session_id = str(data.get('booking_session_id') or '').strip()
        if not re.match(r'^[A-Za-z0-9_-]{8,64}$', session_id):
            raise ValidationError('booking_session_id must be an 8–64 character session token.')

        mobile = cls._normalize_mobile(data.get('mobile'))
        if len(mobile) != 10 or mobile[0] not in '6789':
            raise ValidationError('Enter a valid 10-digit Indian mobile number.')

        name = cls._sanitize_name(data.get('name')) or cls.PLACEHOLDER_NAME
        service = str(data.get('service') or '').strip() or cls.DEFAULT_SERVICE
        notes = str(data.get('notes') or data.get('message') or '').strip()
        if len(notes) < 10:
            notes = cls.AUTO_NOTE

        fields = cls.normalize_payload({
            **data,
            'name': name,
            'mobile': mobile,
            'service': service,
            'notes': notes,
        })
        fields['booking_session_id'] = session_id
        return fields

    @classmethod
    def upsert_inquiry(cls, data: dict[str, Any], user=None) -> tuple[DeepCleaningInquiry, bool]:
        """
        One DeepCleaning99 lead per browser session.
        A 10-digit mobile creates the lead immediately; later fields update it.
        """
        fields = cls.normalize_capture_payload(data)
        session_id = fields['booking_session_id']
        existing = (
            DeepCleaningInquiry.objects.filter(booking_session_id=session_id)
            .order_by('-created_at')
            .first()
        )
        if existing is not None:
            if existing.status in (
                DeepCleaningInquiry.InquiryStatus.CONVERTED,
                DeepCleaningInquiry.InquiryStatus.CLOSED,
            ):
                return existing, False

            update_fields = []
            previous_mobile = existing.mobile
            for key, value in fields.items():
                if key in ('status', 'booking_session_id', 'is_read', 'source'):
                    continue
                if key == 'name':
                    if cls._is_placeholder_name(value):
                        continue
                elif key == 'notes' and value == cls.AUTO_NOTE and (existing.notes or '').strip():
                    continue
                elif value in (None, '') and key not in ('mobile', 'city', 'service'):
                    continue
                if getattr(existing, key) != value:
                    setattr(existing, key, value)
                    update_fields.append(key)
            mobile_changed = 'mobile' in update_fields and previous_mobile != existing.mobile
            if update_fields:
                if mobile_changed and existing.is_read:
                    existing.is_read = False
                    update_fields.append('is_read')
                existing.full_clean()
                update_fields.append('updated_at')
                existing.save(update_fields=update_fields)
            if mobile_changed:
                cls._notify(existing)
            return existing, False

        inquiry = cls.create_inquiry(fields, user=user)
        return inquiry, True

    @staticmethod
    def _notify(inquiry: DeepCleaningInquiry) -> None:
        """Telegram + staff WhatsApp. Failures stay on the lead and never block capture."""
        message = inquiry.notes or DeepCleaningInquiryService.AUTO_NOTE
        service = f"Deep Cleaning — {inquiry.service}"
        try:
            from .telegram import notify_new_inquiry

            notify_new_inquiry(
                name=inquiry.name,
                mobile=inquiry.mobile,
                city=inquiry.city,
                service=service,
                message=message,
                email=inquiry.email,
                premise_type=inquiry.segment,
                premise_size=inquiry.property_size,
                estimated_price=str(inquiry.estimated_price) if inquiry.estimated_price else None,
                service_frequency=inquiry.plan,
            )
        except Exception:
            pass
        try:
            from .whatsflow_pc99 import notify_staff_website_lead

            notify_staff_website_lead(
                inquiry_id=f'dc-{inquiry.id}',
                name=inquiry.name,
                mobile=inquiry.mobile,
                city=inquiry.city,
                service=service,
                property_type=inquiry.segment or 'Residential',
                message=message,
            )
        except Exception:
            pass

    @staticmethod
    def add_remark(inquiry: DeepCleaningInquiry, text: str, user=None) -> DeepCleaningInquiryRemark:
        cleaned = (text or '').strip()
        if not cleaned:
            raise ValidationError('Remark text is required.')
        entry = DeepCleaningInquiryRemark.objects.create(
            inquiry=inquiry,
            remark=cleaned,
            created_by=user,
            remark_type=RemarkType.NOTE,
        )
        DeepCleaningInquiry.objects.filter(pk=inquiry.pk).update(updated_at=entry.updated_at)
        return entry


class DeepCleaningBookingService:
    """Desk workflow for Deep Cleaning bookings. No partner app."""

    COPY_FIELDS = (
        'name', 'mobile', 'email', 'city', 'area', 'address',
        'segment', 'service', 'package_name', 'package_id',
        'quantity', 'unit', 'plan', 'property_size', 'property_type',
        'preferred_date', 'preferred_time', 'notes',
    )

    @classmethod
    def confirm_inquiry(cls, inquiry: DeepCleaningInquiry, user=None) -> tuple[DeepCleaningBooking, bool]:
        with transaction.atomic():
            locked = DeepCleaningInquiry.objects.select_for_update().get(pk=inquiry.pk)
            existing = DeepCleaningBooking.objects.filter(inquiry=locked).first()
            if existing:
                return existing, False
            if locked.status == DeepCleaningInquiry.InquiryStatus.CLOSED:
                raise ValidationError('A closed inquiry cannot become a booking.')
            payload = {field: getattr(locked, field) for field in cls.COPY_FIELDS}
            booking = DeepCleaningBooking.objects.create(
                inquiry=locked,
                created_by=user if getattr(user, 'is_authenticated', False) else None,
                status=DeepCleaningBooking.Status.PENDING,
                price=locked.estimated_price,
                **payload,
            )
            locked.status = DeepCleaningInquiry.InquiryStatus.CONVERTED
            locked.is_read = True
            locked.save(update_fields=['status', 'is_read', 'updated_at'])
            return booking, True

    @staticmethod
    def _lock_booking(booking: DeepCleaningBooking) -> DeepCleaningBooking:
        return DeepCleaningBooking.objects.select_for_update().get(pk=booking.pk)

    @classmethod
    def assign(cls, booking: DeepCleaningBooking, technician: DeepCleaningTechnician) -> DeepCleaningBooking:
        with transaction.atomic():
            locked = cls._lock_booking(booking)
            if locked.status in (
                DeepCleaningBooking.Status.DONE,
                DeepCleaningBooking.Status.CANCELLED,
            ):
                raise ValidationError('This booking can no longer be assigned.')
            tech = DeepCleaningTechnician.objects.select_for_update().get(pk=technician.pk)
            if not tech.is_available_for_work:
                reason = (
                    'inactive'
                    if not tech.is_active
                    else tech.get_presence_status_display()
                )
                raise ValidationError(f'{tech.name} is {reason} and cannot be assigned.')
            services = tech.services or []
            if locked.service not in services:
                raise ValidationError(f'{tech.name} is not set up for {locked.service}.')
            cities = tech.cities or []
            if locked.city and locked.city not in cities:
                raise ValidationError(f'{tech.name} does not cover {locked.city}.')
            locked.technician = tech
            locked.status = DeepCleaningBooking.Status.ON_PROCESS
            locked.assigned_at = timezone.now()
            locked.save(update_fields=['technician', 'status', 'assigned_at', 'updated_at'])
            return locked

    @classmethod
    def unassign(cls, booking: DeepCleaningBooking) -> DeepCleaningBooking:
        with transaction.atomic():
            locked = cls._lock_booking(booking)
            if locked.status != DeepCleaningBooking.Status.ON_PROCESS:
                raise ValidationError('Only an On Process booking can be unassigned.')
            locked.technician = None
            locked.status = DeepCleaningBooking.Status.PENDING
            locked.assigned_at = None
            locked.save(update_fields=['technician', 'status', 'assigned_at', 'updated_at'])
            return locked

    @classmethod
    def complete(cls, booking: DeepCleaningBooking) -> DeepCleaningBooking:
        with transaction.atomic():
            locked = cls._lock_booking(booking)
            if locked.status != DeepCleaningBooking.Status.ON_PROCESS or not locked.technician_id:
                raise ValidationError('Assign a technician before marking this booking done.')
            locked.status = DeepCleaningBooking.Status.DONE
            locked.completed_at = timezone.now()
            locked.save(update_fields=['status', 'completed_at', 'updated_at'])
            return locked

    @classmethod
    def cancel(cls, booking: DeepCleaningBooking) -> DeepCleaningBooking:
        with transaction.atomic():
            locked = cls._lock_booking(booking)
            if locked.status == DeepCleaningBooking.Status.DONE:
                raise ValidationError('A finished booking stays in Done.')
            if locked.status == DeepCleaningBooking.Status.CANCELLED:
                return locked
            locked.technician = None
            locked.status = DeepCleaningBooking.Status.CANCELLED
            locked.assigned_at = None
            locked.save(update_fields=['technician', 'status', 'assigned_at', 'updated_at'])
            return locked
