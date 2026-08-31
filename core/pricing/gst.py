"""GST breakdown helpers for Pricing Master rates."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

MONEY_QUANT = Decimal('0.01')
DEFAULT_GST_PERCENT = Decimal('18.00')


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0.00')


def gst_breakdown(
    amount,
    *,
    gst_percent=DEFAULT_GST_PERCENT,
    price_includes_gst: bool = True,
) -> dict[str, Any]:
    """
    Split a selling amount into base, GST, and customer-facing total.

    - price_includes_gst=True  → amount is tax-inclusive total
    - price_includes_gst=False → amount is base; GST is added on top
    """
    selling = _money(amount)
    rate = _money(gst_percent)
    if rate < 0:
        rate = Decimal('0.00')

    if selling <= 0 or rate <= 0:
        return {
            'amount': selling,
            'gst_percent': rate,
            'price_includes_gst': bool(price_includes_gst),
            'base_amount': selling,
            'gst_amount': Decimal('0.00'),
            'total_with_gst': selling,
        }

    if price_includes_gst:
        base = (selling / (Decimal('1') + rate / Decimal('100'))).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP,
        )
        gst_amount = (selling - base).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        total = selling
    else:
        base = selling
        gst_amount = (selling * rate / Decimal('100')).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP,
        )
        total = (base + gst_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    return {
        'amount': selling,
        'gst_percent': rate,
        'price_includes_gst': bool(price_includes_gst),
        'base_amount': base,
        'gst_amount': gst_amount,
        'total_with_gst': total,
    }


def rate_gst_payload(rate) -> dict[str, Any]:
    """Serialize GST fields + computed breakdown for a PricingRate instance."""
    breakdown = gst_breakdown(
        rate.amount,
        gst_percent=getattr(rate, 'gst_percent', DEFAULT_GST_PERCENT),
        price_includes_gst=getattr(rate, 'price_includes_gst', True),
    )
    return {
        'amount': str(breakdown['amount']),
        'gst_percent': str(breakdown['gst_percent']),
        'price_includes_gst': breakdown['price_includes_gst'],
        'base_amount': str(breakdown['base_amount']),
        'gst_amount': str(breakdown['gst_amount']),
        'total_with_gst': str(breakdown['total_with_gst']),
    }
