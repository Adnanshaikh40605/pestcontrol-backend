"""GST breakdown helpers for Pricing Master rates."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# Ledger GET serializes every visit, and each row asks Pricing Master several
# times for the same service/plan/area. Hold those results for one request so
# a busy technician's report does not time out. Unset outside that request so
# tests and later price edits are not stuck with a process-wide cache.
_pricing_cache: ContextVar[dict | None] = ContextVar('pricing_lookup_cache', default=None)

MONEY_QUANT = Decimal('0.01')
DEFAULT_GST_PERCENT = Decimal('18.00')
GST_INCLUSIVE = 'GST_INCLUSIVE'
GST_EXCLUSIVE = 'GST_EXCLUSIVE'


@contextmanager
def pricing_lookup_cache():
    """Reuse Pricing Master lookups for the rest of this request."""
    existing = _pricing_cache.get()
    if existing is not None:
        yield existing
        return
    token = _pricing_cache.set({})
    try:
        yield
    finally:
        _pricing_cache.reset(token)


def _cached_pricing_lookup(key, loader):
    cache = _pricing_cache.get()
    if cache is None:
        return loader()
    if key in cache:
        cached = cache[key]
        return dict(cached) if isinstance(cached, dict) else cached
    value = loader()
    if isinstance(value, dict):
        cache[key] = dict(value)
        return dict(value)
    cache[key] = value
    return value


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


def parse_gst_pricing_mode(value) -> str:
    """Accept only GST Inclusive or GST Exclusive. Blank means Inclusive."""
    text = str(value or '').strip().upper().replace(' ', '_').replace('-', '_')
    if text in ('', 'GST_INCLUSIVE', 'INCLUSIVE'):
        return GST_INCLUSIVE
    if text in ('GST_EXCLUSIVE', 'EXCLUSIVE'):
        return GST_EXCLUSIVE
    raise ValueError('GST mode must be GST Inclusive or GST Exclusive.')


def quote_entered_price(entered, *, gst_mode, gst_percent=DEFAULT_GST_PERCENT) -> dict[str, Any]:
    """Turn one entered service price into the saved GST snapshot.

    Inclusive: the entered figure is the customer payable. GST is taken out of it.
    Exclusive: the entered figure is before GST. GST is added on top.
    """
    mode = parse_gst_pricing_mode(gst_mode)
    entered_amount = _money(entered)
    breakdown = gst_breakdown(
        entered_amount,
        gst_percent=gst_percent,
        price_includes_gst=(mode == GST_INCLUSIVE),
    )
    return {
        'gst_mode': mode,
        'gst_rate': breakdown['gst_percent'],
        'original_service_price': entered_amount,
        'taxable_amount': breakdown['base_amount'],
        'gst_amount': breakdown['gst_amount'],
        'final_payable_amount': breakdown['total_with_gst'],
    }


def snapshot_service_gst(items, *, gst_mode, gst_percent=DEFAULT_GST_PERCENT) -> dict[str, Any]:
    """Save GST on each service line, then the booking total from those lines.

    The entered price is base minus discount. The returned price string is the
    customer payable. Existing invoice, payment, and ledger reads use that price.
    """
    mode = parse_gst_pricing_mode(gst_mode)
    rate = _money(gst_percent)
    if rate < 0:
        rate = Decimal('0.00')

    entered_total = Decimal('0.00')
    taxable_total = Decimal('0.00')
    gst_total = Decimal('0.00')
    final_total = Decimal('0.00')

    for item in items:
        if not isinstance(item, dict):
            continue
        base = _money(item.get('base_amount', item.get('baseAmount')))
        discount = _money(item.get('discount'))
        if discount > base > 0:
            discount = base
        entered = (base - discount) if base > 0 else _money(item.get('amount'))
        entered = _money(entered)
        quote = quote_entered_price(entered, gst_mode=mode, gst_percent=rate)
        if base <= 0:
            item['base_amount'] = float(entered)
            item['discount'] = 0.0
        item['amount'] = float(quote['final_payable_amount'])
        item['gst_mode'] = mode
        item['gst_rate'] = str(quote['gst_rate'])
        item['taxable_amount'] = str(quote['taxable_amount'])
        item['gst_amount'] = str(quote['gst_amount'])
        item['final_amount'] = str(quote['final_payable_amount'])
        entered_total += quote['original_service_price']
        taxable_total += quote['taxable_amount']
        gst_total += quote['gst_amount']
        final_total += quote['final_payable_amount']

    return {
        'gst_mode': mode,
        'gst_rate': rate,
        'original_service_price': _money(entered_total),
        'taxable_amount': _money(taxable_total),
        'gst_amount': _money(gst_total),
        'final_payable_amount': _money(final_total),
        'overridden_price': None,
        'price': f'{_money(final_total):.2f}',
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


def _close_money(left, right, *, rel=Decimal('0.01'), abs_tol=Decimal('1.00')) -> bool:
    a = _money(left)
    b = _money(right)
    if a <= 0 or b <= 0:
        return a == b
    gap = abs(a - b)
    return gap <= abs_tol or gap <= (max(a, b) * rel)


def explicit_service_base_total(job) -> Decimal | None:
    """Sum of service_items.base_amount when the booking stored an explicit base.

    ``amount`` alone is not enough — older rows stored the customer total there.
    """
    items = getattr(job, 'service_items', None) or []
    if not isinstance(items, list):
        return None
    found = False
    total = Decimal('0.00')
    for item in items:
        if not isinstance(item, dict):
            continue
        if 'base_amount' not in item and 'baseAmount' not in item:
            continue
        raw = item.get('base_amount', item.get('baseAmount'))
        found = True
        total += _money(raw)
    if not found or total <= 0:
        return None
    return total


def chart_quote_for_job(job) -> dict[str, Any] | None:
    """Active Pricing Master quote for this job's service + plan + size.

    Returns the configured base, GST and customer total. None when the live
    chart has no row — callers must not invent a price.
    """
    if job is None:
        return None
    try:
        from core.models import PricingRate
        from core.pricing.aliases import canonical_service_line, clean_service_label
        from core.pricing.db import pricing_region_for_city, resolve_pricing_region_slug
    except Exception:
        return None

    items = getattr(job, 'service_items', None) or []
    item = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
    service = clean_service_label(
        str(item.get('service') or getattr(job, 'source_service', None) or getattr(job, 'service_type', None) or '')
    )
    plan = str(item.get('plan') or item.get('frequency') or '').strip()
    area = str(item.get('area') or getattr(job, 'bhk_size', None) or '').strip()
    if not service or not plan or not area:
        return None

    canonical = canonical_service_line(service)
    names = tuple(sorted({service, canonical}))
    city = None
    master_city = getattr(job, 'master_city', None)
    if master_city is not None and getattr(master_city, 'name', None):
        city = master_city.name
    elif getattr(job, 'city', None):
        city = job.city

    def _load():
        slug = resolve_pricing_region_slug(pricing_region_for_city(city) if city else None) or 'mumbai'
        rate = (
            PricingRate.objects.filter(
                is_active=True,
                region__slug=slug,
                plan_type=plan,
                area_key=area,
                service_package__in=list(names),
            )
            .order_by('-id')
            .first()
        )
        if rate is None:
            rate = (
                PricingRate.objects.filter(
                    is_active=True,
                    plan_type=plan,
                    area_key=area,
                    service_package__in=list(names),
                )
                .order_by('-id')
                .first()
            )
        if rate is None:
            return None
        return gst_breakdown(
            rate.amount,
            gst_percent=getattr(rate, 'gst_percent', DEFAULT_GST_PERCENT),
            price_includes_gst=getattr(rate, 'price_includes_gst', True),
        )

    return _cached_pricing_lookup(('chart', city or '', plan, area, names), _load)


def _visit_slice_matches(amount: Decimal, package: Decimal) -> bool:
    """True when ``amount`` is the package or package ÷ a known visit count."""
    if package <= 0 or amount <= 0:
        return False
    if _close_money(amount, package):
        return True
    for count in (2, 3, 4, 6, 9, 12, 24, 48):
        if _close_money(amount, package / Decimal(count)):
            return True
    return False


def ledger_base_ratio(job, amount) -> Decimal:
    """Multiply a ledger figure by this to show the configured service base.

    - Amount already equal to the stored or chart base (or a visit slice of it): 1
    - Amount is the customer total (base + GST) while a chart base exists: base ÷ amount
    - No stored base and no chart row: peel GST the legacy way (inclusive totals)

    Does not invent a base by hardcoding 18% when a chart or stored base exists.
    """
    figure = _money(amount)
    if figure <= 0:
        return Decimal('1')

    chart = chart_quote_for_job(job) if job is not None else None
    stored = explicit_service_base_total(job) if job is not None else None

    if chart is not None:
        chart_base = _money(chart['base_amount'])
        chart_total = _money(chart['total_with_gst'])
        # Trust the chart base only when the booking stored that base.
        # A staff price that merely equals some other rate is still the old
        # inclusive total and must keep the legacy GST peel.
        if (
            stored
            and chart_base > 0
            and (
                _visit_slice_matches(figure, chart_base)
                or (_close_money(stored, chart_base) and _visit_slice_matches(figure, stored))
            )
        ):
            return Decimal('1')
        # Stored "base" or this figure is the GST-inclusive customer total.
        if chart_total > 0 and chart_base > 0 and (
            _close_money(figure, chart_total)
            or (stored is not None and _close_money(stored, chart_total) and _visit_slice_matches(figure, stored))
        ):
            target = chart_base if _close_money(figure, chart_total) else (
                chart_base * (figure / stored) if stored else chart_base
            )
            # Visit slice of an inclusive package: same share of the chart base.
            if stored and _visit_slice_matches(figure, stored) and not _close_money(figure, chart_total):
                target = (chart_base * figure / stored).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            return (target / figure) if figure else Decimal('1')

    if stored and stored > 0 and _visit_slice_matches(figure, stored):
        # Explicit base on the booking. Do not peel GST off it again.
        return Decimal('1')

    if job is None:
        base = amount_excluding_gst(figure)
        return base / figure if figure else Decimal('1')

    # Legacy rows stored only the customer total.
    base = amount_excluding_gst(figure, resolve_job_gst_percent(job))
    return (base / figure) if figure else Decimal('1')


def ledger_reference_amount(job) -> Decimal:
    """Booking figure the ledger ratio is taken from (staff price, else visit revenue)."""
    if job is None:
        return Decimal('0.00')
    try:
        from core.payment_utils import parse_jobcard_price
    except Exception:
        parse_jobcard_price = None
    price = (
        parse_jobcard_price(getattr(job, 'price', None))
        if parse_jobcard_price is not None
        else _money(getattr(job, 'price', None))
    )
    if price > 0:
        return price
    return _money(getattr(job, 'visit_revenue_amount', None))


def apply_ledger_base(job, amount, reference=None) -> Decimal:
    """Map one stored rupee figure onto the technician-ledger base.

    Uses the same ratio as the ledger (stored/chart base, or one GST peel for
    legacy inclusive totals). Shares are scaled from the booking reference so a
    40% slice is not peeled a second time.
    """
    figure = _money(amount)
    if figure <= 0 or job is None:
        if figure <= 0:
            return figure
        return amount_excluding_gst(figure)

    ref = _money(reference) if reference is not None else ledger_reference_amount(job)
    if ref <= 0:
        ref = figure

    stored = explicit_service_base_total(job)
    chart = chart_quote_for_job(job)
    chart_total = _money(chart['total_with_gst']) if chart is not None else None
    replaces_customer_total = bool(
        chart_total
        and ref > 0
        and (
            _close_money(ref, chart_total)
            or (stored and _close_money(stored, chart_total))
        )
    )
    if stored or replaces_customer_total:
        ratio = ledger_base_ratio(job, ref)
        return (figure * ratio).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return amount_excluding_gst(figure, resolve_job_gst_percent(job))


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


def partner_customer_gst_fields(job, inclusive_amount=None) -> dict[str, str]:
    """
    Customer payable split for Partner App (Cash/Online collection UI).

    JobCard.price / total_booking_amount are GST-inclusive. Returns string
    fields ready to inject into partner booking list/detail payloads.
    """
    if inclusive_amount is None:
        from core.payment_utils import partner_booking_display_amount

        inclusive_amount = partner_booking_display_amount(job)
    figure = _money(inclusive_amount)
    chart = chart_quote_for_job(job) if job is not None else None
    stored = explicit_service_base_total(job) if job is not None else None
    if chart is not None and figure > 0:
        chart_base = _money(chart['base_amount'])
        chart_total = _money(chart['total_with_gst'])
        chart_gst = _money(chart['gst_amount'])
        # Price is already the configured base (cash / rate-card basic).
        if chart_base > 0 and (
            _close_money(figure, chart_base)
            or (stored and _close_money(stored, chart_base) and _visit_slice_matches(figure, stored))
        ):
            bd = {
                'gst_percent': chart['gst_percent'],
                'base_amount': chart_base,
                'gst_amount': chart_gst,
                'total_with_gst': chart_total,
            }
        # Price is the customer total (or within a rupee of the chart total).
        elif chart_total > 0 and chart_base > 0 and (
            _close_money(figure, chart_total)
            or (stored and _close_money(stored, chart_total))
        ):
            bd = {
                'gst_percent': chart['gst_percent'],
                'base_amount': chart_base,
                'gst_amount': chart_gst,
                'total_with_gst': chart_total,
            }
        else:
            bd = None
    else:
        bd = None
    if bd is None:
        gst_percent = resolve_job_gst_percent(job)
        bd = gst_breakdown(
            inclusive_amount,
            gst_percent=gst_percent,
            price_includes_gst=True,
        )
    return {
        'gst_percent': str(bd['gst_percent']),
        'base_amount': str(bd['base_amount']),
        'gst_amount': str(bd['gst_amount']),
        'total_amount': str(bd['total_with_gst']),
    }


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

        def _load_region_gst():
            distinct = list(
                PricingRate.objects.filter(region__slug=slug, is_active=True)
                .values_list('gst_percent', flat=True)
                .distinct()
            )
            if len(distinct) == 1 and distinct[0] is not None:
                return _money(distinct[0])
            return None

        region_gst = _cached_pricing_lookup(('gst-percent', slug), _load_region_gst)
        if region_gst is not None:
            return region_gst
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
    if job is not None:
        return apply_ledger_base(job, amount)
    return amount_excluding_gst(amount, resolve_job_gst_percent(job))
