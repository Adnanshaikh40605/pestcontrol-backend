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
        # Lets the CRM filter Area options by booking type (home vs hotel/office).
        'property_category': getattr(rate, 'property_category', None) or 'residential',
    }


def amount_excluding_gst(amount, gst_percent=DEFAULT_GST_PERCENT) -> Decimal:
    """
    Convert a GST-inclusive rupee amount to the excl-GST base.

    Booking matrix / JobCard.price store the customer payable (total_with_gst).
    Technician Ledger + partner earnings/settlements display the excl-GST base
    so Service ₹ / tech 40% / company 60% are not inflated by tax.
    """
    return gst_breakdown(
        amount,
        gst_percent=gst_percent,
        price_includes_gst=True,
    )['base_amount']


def resolve_job_gst_percent(job=None) -> Decimal:
    """
    GST % used when stripping tax for technician ledger / partner earnings.

    Prefer an explicit rate on service_items when present; otherwise the Pricing
    Master default (DEFAULT_GST_PERCENT, currently 18%) — same source as
    ``core.pricing.gst.gst_breakdown`` / booking matrix.
    """
    if job is None:
        return DEFAULT_GST_PERCENT

    items = getattr(job, 'service_items', None) or []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            raw = item.get('gst_percent', item.get('gstPercent'))
            if raw is None or str(raw).strip() == '':
                continue
            rate = _money(raw)
            if rate >= 0:
                return rate

    # Fall back to the active Pricing Master rate for this region when uniform.
    try:
        from core.models import PricingRate
        from core.pricing.db import pricing_region_for_city, resolve_pricing_region_slug

        city = None
        master_city = getattr(job, 'master_city', None)
        if master_city is not None and getattr(master_city, 'name', None):
            city = master_city.name
        elif getattr(job, 'city', None):
            city = job.city
        slug = resolve_pricing_region_slug(pricing_region_for_city(city) if city else None)
        if not slug:
            slug = 'mumbai'
        distinct = list(
            PricingRate.objects.filter(region__slug=slug, is_active=True)
            .values_list('gst_percent', flat=True)
            .distinct()
        )
        if len(distinct) == 1 and distinct[0] is not None:
            return _money(distinct[0])
    except Exception:
        pass

    return DEFAULT_GST_PERCENT


def earning_amount_excluding_gst(amount, *, earning_type: str | None = None, job=None) -> Decimal:
    """
    Partner earning / settlement line → excl-GST for display.

    Revenue-share lines are derived from GST-inclusive booking totals, so strip
    tax. Flat incentives/deductions are absolute rupees and stay unchanged.
    """
    et = (earning_type or '').strip().lower()
    if et in ('incentive', 'deduction'):
        return _money(amount)
    return amount_excluding_gst(amount, resolve_job_gst_percent(job))
