"""Business logic for DeepCleaning99 website booking inquiries."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date

from .models import DeepCleaningInquiry, DeepCleaningInquiryRemark, RemarkType


class DeepCleaningInquiryService:
    """Create DeepCleaning99 leads without touching pest Inquiry tables."""

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
        inquiry = DeepCleaningInquiry(created_by=user, **fields)
        inquiry.full_clean()
        inquiry.save()
        return inquiry

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
