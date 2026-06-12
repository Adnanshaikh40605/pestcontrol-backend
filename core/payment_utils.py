"""Helpers for booking payment collection and validation."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Tuple

from django.core.exceptions import ValidationError


MONEY_QUANT = Decimal('0.01')


def parse_jobcard_price(price_value) -> Decimal:
    """Parse JobCard.price (string/number) into a non-negative Decimal."""
    if price_value is None:
        return Decimal('0.00')
    raw = str(price_value).replace('₹', '').replace(',', '').strip()
    if not raw:
        return Decimal('0.00')
    try:
        amount = Decimal(raw).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')
    if amount < 0:
        return Decimal('0.00')
    return amount


def quantize_money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def validate_payment_amounts(
    total: Decimal,
    paid: Decimal,
    pending: Decimal,
) -> None:
    """Raise ValidationError when paid/pending are invalid for the service total."""
    total = quantize_money(total)
    paid = quantize_money(paid)
    pending = quantize_money(pending)

    if total < 0 or paid < 0 or pending < 0:
        raise ValidationError('Payment amounts cannot be negative.')

    if paid > total:
        raise ValidationError('Paid amount cannot exceed total service amount.')

    if pending > total:
        raise ValidationError('Pending amount cannot exceed total service amount.')

    if paid + pending != total:
        raise ValidationError(
            f'Paid amount (₹{paid}) and pending amount (₹{pending}) must equal '
            f'total service amount (₹{total}).'
        )


def derive_payment_status(paid: Decimal, pending: Decimal, total: Decimal) -> str:
    """Map paid/pending balances to JobCard.PaymentStatus value."""
    from .models import JobCard

    paid = quantize_money(paid)
    pending = quantize_money(pending)
    total = quantize_money(total)

    if total <= 0 or pending <= 0:
        return JobCard.PaymentStatus.PAID
    if paid <= 0:
        return JobCard.PaymentStatus.PENDING
    return JobCard.PaymentStatus.PARTIALLY_PAID


def payment_status_label(status: str, pending: Decimal) -> str:
    """Human-readable payment status for CRM."""
    from .models import JobCard

    if status == JobCard.PaymentStatus.PAID or quantize_money(pending) <= 0:
        return 'Fully Paid'
    if status == JobCard.PaymentStatus.PARTIALLY_PAID:
        return 'Partially Paid'
    if status in (JobCard.PaymentStatus.PENDING, JobCard.PaymentStatus.UNPAID):
        return 'Pending'
    return status


def resolve_completion_amounts(
    total: Decimal,
    collection_type: Optional[str],
    paid_amount: Optional[Decimal] = None,
    pending_amount: Optional[Decimal] = None,
) -> Tuple[Decimal, Decimal]:
    """
    Compute paid/pending for booking completion.
    collection_type: full | half | custom
    """
    total = quantize_money(total)
    collection_type = (collection_type or 'full').strip().lower()

    if collection_type == 'full':
        return total, Decimal('0.00')

    if collection_type == 'half':
        half = (total / 2).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        return half, total - half

    # custom — caller must supply one of paid_amount or pending_amount
    if paid_amount is not None and pending_amount is None:
        paid = quantize_money(paid_amount)
        pending = total - paid
    elif pending_amount is not None and paid_amount is None:
        pending = quantize_money(pending_amount)
        paid = total - pending
    elif paid_amount is not None and pending_amount is not None:
        paid = quantize_money(paid_amount)
        pending = quantize_money(pending_amount)
    else:
        raise ValidationError(
            'For custom payment, provide either paid_amount or pending_amount.'
        )

    validate_payment_amounts(total, paid, pending)
    return paid, pending
