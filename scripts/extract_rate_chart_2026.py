"""Flatten the 2026 master rate chart (.numbers) into the CSV the importer reads.

Run this only when the workbook changes; the generated CSV is committed so that
importing needs neither Numbers nor the numbers-parser package:

    python3 scripts/extract_rate_chart_2026.py \
        "Pestcontrol99_Complete_GST_Rate_Chart_2026 (1).numbers" \
        core/pricing/data/rate_chart_2026.csv

Every sheet states a GST-exclusive "Recommended Basic", a 18% GST column and a
final payable. We keep the basic and let the CRM derive GST, so the workbook's
GST/total columns are used only to verify we read the right cells.
"""
from __future__ import annotations

import csv
import re
import sys
from decimal import Decimal
from pathlib import Path

GST_PERCENT = Decimal('18.00')

# Sheets that hold no rates: a costing model and a provenance/terms list.
SKIP_SHEETS = {'Pricing Guide', 'Quote Calculator', 'Sources & Terms'}

FIELDS = [
    'property_category',
    'service_package',
    'plan_type',
    'area_key',
    'amount',
    'floor_amount',
    'gst_percent',
    'billing_basis',
    'notes',
    'source_sheet',
    'source_row',
    'expected_gst',
    'expected_total',
]


def dashes(text: str) -> str:
    """Normalise em/en dashes so keys are ASCII and stay under max_length."""
    return re.sub(r'\s*[—–]\s*', lambda m: ' - ' if ' ' in m.group(0) else '-', text).strip()


def plan(label: str) -> str:
    """Map a workbook frequency onto the CRM's plan vocabulary.

    Capitalisation is forced because the sheets spell the same package both ways
    ("4 visits/month" and "4 Visits/Month"), which would otherwise land as two
    different plans on the same service.
    """
    clean = dashes(str(label)).strip()
    if clean.lower() in {'one-time', 'one time', 'one-time package', 'one time package'}:
        return 'One Time Service'
    words = []
    for word in clean.split():
        if word.isupper() or word == '-':
            words.append(word)
        else:
            words.append('/'.join(p.capitalize() for p in word.split('/')))
    return ' '.join(words)


# Three sheets name the same work differently. Left as-is they become separate
# entries in the booking service list, so the operator sees "Bed Bugs" three
# times. The service is the treatment; the property it happens in is the area.
SERVICE_ALIASES = {
    'Bed Bug Package': 'Bed Bugs',
    'Bed Bug Package - 2 services': 'Bed Bugs',
    'Thermal Fogging': 'Mosquito Thermal Fogging',
}

# The society sheet names its plans as if they were the only IPM tiers, so in the
# booking service list "Complete IPM" gave no hint that it is common-area work
# for a housing society. Keyed by category because the same tier names could
# later appear for another segment.
CATEGORY_SERVICE_ALIASES = {
    ('society', 'Complete IPM'): 'Complete IPM Society',
    ('society', 'Essential IPM'): 'Essential IPM Society',
}

# Priced in the chart but deliberately not offered: societies book rodent work as
# part of an IPM plan rather than on its own. Dropping it here rather than
# deactivating the rows keeps a re-import from bringing it back.
EXCLUDED_SERVICES = {
    ('society', 'Rodent Control'),
}


def money(value) -> Decimal | None:
    if value in (None, ''):
        return None
    return Decimal(str(round(float(value), 2)))


def visits(value) -> int:
    return int(round(float(value)))


class Rows:
    def __init__(self) -> None:
        self.out: list[dict] = []

    def add(self, *, sheet, row, category, service, plan_type, area,
            amount, floor=None, basic_gst=None, basic_total=None,
            billing_basis='', notes=''):
        if amount is None:
            return
        name = dashes(str(service))
        name = SERVICE_ALIASES.get(name, name)
        name = CATEGORY_SERVICE_ALIASES.get((category, name), name)
        if (category, name) in EXCLUDED_SERVICES:
            return
        self.out.append({
            'property_category': category,
            'service_package': name,
            'plan_type': plan_type,
            'area_key': dashes(str(area)),
            'amount': f'{amount:.2f}',
            'floor_amount': '' if floor is None else f'{floor:.2f}',
            'gst_percent': f'{GST_PERCENT:.2f}',
            'billing_basis': dashes(str(billing_basis or '')),
            'notes': dashes(str(notes or '')),
            'source_sheet': sheet,
            'source_row': row,
            'expected_gst': '' if basic_gst is None else f'{basic_gst:.2f}',
            'expected_total': '' if basic_total is None else f'{basic_total:.2f}',
        })


def residential(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[3]:
            continue
        service, area, scope = r[0], r[1], r[2]
        rows.add(sheet='Residential', row=i, category='residential', service=service,
                 plan_type='One Time Service', area=area,
                 amount=money(r[3]), floor=money(r[4]),
                 basic_gst=money(r[5]), basic_total=money(r[6]), notes=scope)

        # Bed bug and termite repeat the one-time price in the AMC columns; the
        # workbook's own terms say that work is scoped separately and is not an
        # AMC, so an identical "AMC" row would be a phantom package.
        amc_basic, one_time = money(r[8]), money(r[3])
        if amc_basic is None or amc_basic == one_time:
            continue
        n = visits(r[7])
        rows.add(sheet='Residential', row=i, category='residential', service=service,
                 plan_type=f'AMC {n} Service' + ('s' if n != 1 else ''), area=area,
                 amount=amc_basic, floor=money(r[9]),
                 basic_gst=money(r[10]), basic_total=money(r[11]), notes=scope)


def society(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[5]:
            continue
        rows.add(sheet='Society', row=i, category='society', service=r[0],
                 plan_type=plan(r[3]), area=r[1],
                 amount=money(r[5]), floor=money(r[6]),
                 basic_gst=money(r[7]), basic_total=money(r[8]),
                 notes=f'{r[2]}. {r[4]}')


def hospital(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[5]:
            continue
        rows.add(sheet='Hospital & Clinic', row=i, category='hospital', service=r[2],
                 plan_type=plan(r[4]), area=f'{r[0]} - {r[1]}',
                 amount=money(r[5]), floor=money(r[7]),
                 basic_gst=money(r[8]), basic_total=money(r[9]),
                 billing_basis=r[6], notes=r[3])


def hotel(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[4]:
            continue
        rows.add(sheet='Hotel & Restaurant', row=i, category='hotel', service=r[2],
                 plan_type=plan(r[3]), area=f'{r[0]} - {r[1]}',
                 amount=money(r[4]), floor=money(r[6]),
                 basic_gst=money(r[7]), basic_total=money(r[8]), notes=r[5])


def corporate_one_time(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[5]:
            continue
        rows.add(sheet='Corporate One-Time', row=i, category='corporate', service=r[3],
                 plan_type='One Time Service', area=f'{r[0]} - {r[1]}',
                 amount=money(r[5]), floor=money(r[6]),
                 basic_gst=money(r[7]), basic_total=money(r[8]),
                 notes=f'{r[2]}. {r[4]}')


def corporate_monthly(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[6]:
            continue
        rows.add(sheet='Corporate Monthly', row=i, category='corporate_monthly', service=r[4],
                 plan_type=f'{visits(r[3])} Visits/Month', area=f'{r[0]} - {r[1]}',
                 amount=money(r[6]), floor=money(r[7]),
                 basic_gst=money(r[8]), basic_total=money(r[9]),
                 billing_basis='Per month',
                 notes=f'{r[2]}. {r[5]}. {r[10]}')


def multi_site(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[3]:
            continue
        # Column A is the kind of site, not a service. The service being sold to
        # a chain is Integrated IPM; the site type and outlet band size it.
        rows.add(sheet='Multi-Site Chains', row=i, category='multi_site',
                 service='Integrated IPM',
                 plan_type=f'{visits(r[2])} Visits/Month',
                 area=f'{dashes(str(r[0]))} - {dashes(str(r[1]))} Outlets',
                 amount=money(r[3]), floor=money(r[4]),
                 basic_gst=money(r[5]), basic_total=money(r[6]),
                 billing_basis='Per outlet/month', notes=r[7])


def addons(t, rows: Rows) -> None:
    for i, r in enumerate(t.rows(values_only=True)):
        if i < 4 or not r[0] or not r[2]:
            continue
        # No floor column here: add-ons are quoted to protect margin, not negotiated.
        rows.add(sheet='Add-ons', row=i, category='addon', service=r[0],
                 plan_type='Add-On', area=r[1],
                 amount=money(r[2]), floor=None,
                 basic_gst=money(r[3]), basic_total=money(r[4]),
                 billing_basis=r[1], notes=r[5])


HANDLERS = {
    'Residential': residential,
    'Society': society,
    'Hospital & Clinic': hospital,
    'Hotel & Restaurant': hotel,
    'Corporate One-Time': corporate_one_time,
    'Corporate Monthly': corporate_monthly,
    'Multi-Site Chains': multi_site,
    'Add-ons': addons,
}

MAX_LEN = {'service_package': 100, 'plan_type': 50, 'area_key': 100}


def main() -> int:
    from numbers_parser import Document

    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    rows = Rows()
    for sheet in Document(str(src)).sheets:
        if sheet.name in SKIP_SHEETS:
            continue
        handler = HANDLERS.get(sheet.name)
        if handler is None:
            print(f'!! no handler for sheet {sheet.name!r}')
            continue
        before = len(rows.out)
        handler(sheet.tables[0], rows)
        print(f'{sheet.name:<22} -> {len(rows.out) - before:>3} rates')

    problems = 0

    # The workbook computes GST on the basic; if our column picks were wrong the
    # arithmetic would not reproduce, so this is the real guard on the mapping.
    for row in rows.out:
        basic = Decimal(row['amount'])
        want_gst, want_total = row['expected_gst'], row['expected_total']
        if want_gst:
            gst = (basic * GST_PERCENT / 100).quantize(Decimal('0.01'))
            if abs(gst - Decimal(want_gst)) > Decimal('0.51'):
                print(f'!! GST mismatch {row["source_sheet"]} r{row["source_row"]}: '
                      f'{basic} -> {gst} vs sheet {want_gst}')
                problems += 1
        if want_total:
            total = (basic + basic * GST_PERCENT / 100).quantize(Decimal('0.01'))
            if abs(total - Decimal(want_total)) > Decimal('0.51'):
                print(f'!! total mismatch {row["source_sheet"]} r{row["source_row"]}: '
                      f'{basic} -> {total} vs sheet {want_total}')
                problems += 1
        if row['floor_amount'] and Decimal(row['floor_amount']) > basic:
            print(f'!! floor above basic {row["source_sheet"]} r{row["source_row"]}')
            problems += 1
        for field, limit in MAX_LEN.items():
            if len(row[field]) > limit:
                print(f'!! {field} too long ({len(row[field])}>{limit}): {row[field]!r}')
                problems += 1

    # unique_together is (region, service_package, plan_type, area_key).
    seen: dict[tuple, dict] = {}
    for row in rows.out:
        key = (row['service_package'], row['plan_type'], row['area_key'])
        if key in seen:
            prev = seen[key]
            print(f'!! duplicate key {key}\n     {prev["source_sheet"]} r{prev["source_row"]} '
                  f'@{prev["amount"]} vs {row["source_sheet"]} r{row["source_row"]} @{row["amount"]}')
            problems += 1
        seen[key] = row

    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows.out)

    print(f'\n{len(rows.out)} rates -> {dest}')
    print(f'categories: {sorted({r["property_category"] for r in rows.out})}')
    print(f'plans: {sorted({r["plan_type"] for r in rows.out})}')
    print(f'problems: {problems}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
