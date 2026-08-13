"""Immutable stock ledger helpers with balance + FIFO lot updates."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import (
    Branch,
    Chemical,
    ChemicalUsage,
    Equipment,
    StockBalance,
    StockLot,
    StockMovement,
    Supplier,
)
from core.models import JobCard, Technician


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.001'))


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _cost4(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.0001'))


def resolve_branch_for_job(job: JobCard) -> Branch | None:
    from accounts.models import BranchCityMap

    if job.master_city_id:
        mapped = BranchCityMap.objects.filter(city_id=job.master_city_id).select_related('branch').first()
        if mapped:
            return mapped.branch
    city_name = (job.city or '').strip()
    if city_name:
        branch = Branch.objects.filter(name__iexact=city_name, is_active=True).first()
        if branch:
            return branch
        mapped = (
            BranchCityMap.objects.filter(city__name__iexact=city_name)
            .select_related('branch')
            .first()
        )
        if mapped:
            return mapped.branch
    return Branch.objects.filter(is_active=True).order_by('id').first()


def _get_or_create_balance(
    *,
    branch: Branch,
    item_type: str,
    chemical: Chemical | None = None,
    equipment: Equipment | None = None,
) -> StockBalance:
    defaults = {'quantity': Decimal('0')}
    if item_type == StockBalance.ItemType.CHEMICAL:
        bal, _ = StockBalance.objects.get_or_create(
            branch=branch,
            item_type=item_type,
            chemical=chemical,
            defaults=defaults,
        )
    else:
        bal, _ = StockBalance.objects.get_or_create(
            branch=branch,
            item_type=item_type,
            equipment=equipment,
            defaults=defaults,
        )
    return bal


def _apply_balance_delta(
    *,
    branch: Branch,
    item_type: str,
    delta: Decimal,
    chemical: Chemical | None = None,
    equipment: Equipment | None = None,
    allow_negative: bool = False,
) -> StockBalance:
    bal = _get_or_create_balance(
        branch=branch, item_type=item_type, chemical=chemical, equipment=equipment,
    )
    new_qty = _q(bal.quantity) + _q(delta)
    if new_qty < 0 and not allow_negative:
        raise ValidationError('Insufficient stock for this movement.')
    StockBalance.objects.filter(pk=bal.pk).update(quantity=new_qty, updated_at=timezone.now())
    bal.refresh_from_db()
    return bal


def _fifo_consume(
    *,
    branch: Branch,
    chemical: Chemical,
    quantity: Decimal,
) -> list[tuple[StockLot, Decimal, Decimal]]:
    """Return list of (lot, qty, unit_cost) consumed FIFO by expiry then purchase date."""
    remaining = _q(quantity)
    if remaining <= 0:
        raise ValidationError('Quantity must be positive.')
    lots = (
        StockLot.objects.select_for_update()
        .filter(
            branch=branch,
            item_type=StockLot.ItemType.CHEMICAL,
            chemical=chemical,
            qty_remaining__gt=0,
        )
        .order_by(F('expiry_date').asc(nulls_last=True), 'purchased_at', 'id')
    )
    consumed: list[tuple[StockLot, Decimal, Decimal]] = []
    for lot in lots:
        if remaining <= 0:
            break
        take = min(_q(lot.qty_remaining), remaining)
        lot.qty_remaining = _q(lot.qty_remaining) - take
        lot.save(update_fields=['qty_remaining', 'updated_at'])
        consumed.append((lot, take, _cost4(lot.unit_cost)))
        remaining -= take
    if remaining > 0:
        # Fallback: consume without lot at last known cost / zero
        last = (
            StockLot.objects.filter(branch=branch, chemical=chemical)
            .order_by('-purchased_at', '-id')
            .first()
        )
        unit = _cost4(last.unit_cost) if last else Decimal('0')
        consumed.append((None, remaining, unit))  # type: ignore[arg-type]
    return consumed


@transaction.atomic
def purchase_stock(
    *,
    branch: Branch,
    item_type: str,
    quantity,
    unit_cost,
    chemical: Chemical | None = None,
    equipment: Equipment | None = None,
    supplier: Supplier | None = None,
    batch_no: str = '',
    expiry_date=None,
    movement_date=None,
    reference: str = '',
    remarks: str = '',
    payment_pending: bool = False,
    user=None,
) -> StockMovement:
    qty = _q(quantity)
    if qty <= 0:
        raise ValidationError('Purchase quantity must be positive.')
    cost = _cost4(unit_cost)
    movement_date = movement_date or timezone.localdate()
    lot = StockLot.objects.create(
        branch=branch,
        item_type=item_type,
        chemical=chemical,
        equipment=equipment,
        supplier=supplier,
        batch_no=batch_no or '',
        expiry_date=expiry_date,
        unit_cost=cost,
        qty_received=qty,
        qty_remaining=qty,
        purchased_at=movement_date,
    )
    _apply_balance_delta(
        branch=branch, item_type=item_type, delta=qty, chemical=chemical, equipment=equipment,
        allow_negative=True,
    )
    return StockMovement.objects.create(
        movement_type=StockMovement.MovementType.PURCHASE,
        item_type=item_type,
        branch=branch,
        chemical=chemical,
        equipment=equipment,
        lot=lot,
        supplier=supplier,
        quantity=qty,
        unit_cost=cost,
        line_cost=_money(qty * cost),
        movement_date=movement_date,
        reference=reference,
        remarks=remarks,
        payment_pending=payment_pending,
        created_by=user,
    )


@transaction.atomic
def purchase_return(
    *,
    branch: Branch,
    item_type: str,
    quantity,
    chemical: Chemical | None = None,
    equipment: Equipment | None = None,
    lot: StockLot | None = None,
    supplier: Supplier | None = None,
    movement_date=None,
    reference: str = '',
    remarks: str = '',
    user=None,
) -> StockMovement:
    qty = _q(quantity)
    if qty <= 0:
        raise ValidationError('Return quantity must be positive.')
    unit_cost = _cost4(lot.unit_cost) if lot else Decimal('0')
    if lot:
        if _q(lot.qty_remaining) < qty:
            raise ValidationError('Lot does not have enough remaining quantity.')
        lot.qty_remaining = _q(lot.qty_remaining) - qty
        lot.save(update_fields=['qty_remaining', 'updated_at'])
        unit_cost = _cost4(lot.unit_cost)
    _apply_balance_delta(
        branch=branch, item_type=item_type, delta=-qty, chemical=chemical, equipment=equipment,
    )
    return StockMovement.objects.create(
        movement_type=StockMovement.MovementType.PURCHASE_RETURN,
        item_type=item_type,
        branch=branch,
        chemical=chemical,
        equipment=equipment,
        lot=lot,
        supplier=supplier or (lot.supplier if lot else None),
        quantity=qty,
        unit_cost=unit_cost,
        line_cost=_money(qty * unit_cost),
        movement_date=movement_date or timezone.localdate(),
        reference=reference,
        remarks=remarks,
        created_by=user,
    )


@transaction.atomic
def adjust_stock(
    *,
    branch: Branch,
    item_type: str,
    quantity_delta,
    chemical: Chemical | None = None,
    equipment: Equipment | None = None,
    unit_cost=0,
    movement_date=None,
    reference: str = '',
    remarks: str = '',
    user=None,
) -> StockMovement:
    delta = _q(quantity_delta)
    if delta == 0:
        raise ValidationError('Adjustment quantity cannot be zero.')
    _apply_balance_delta(
        branch=branch,
        item_type=item_type,
        delta=delta,
        chemical=chemical,
        equipment=equipment,
        allow_negative=True,
    )
    cost = _cost4(unit_cost)
    return StockMovement.objects.create(
        movement_type=StockMovement.MovementType.ADJUSTMENT,
        item_type=item_type,
        branch=branch,
        chemical=chemical,
        equipment=equipment,
        quantity=abs(delta),
        unit_cost=cost,
        line_cost=_money(abs(delta) * cost),
        movement_date=movement_date or timezone.localdate(),
        reference=reference,
        remarks=remarks or ('Increase' if delta > 0 else 'Decrease'),
        created_by=user,
    )


@transaction.atomic
def issue_stock(
    *,
    branch: Branch,
    chemical: Chemical,
    quantity,
    technician: Technician | None = None,
    jobcard: JobCard | None = None,
    movement_date=None,
    reference: str = '',
    remarks: str = '',
    user=None,
) -> list[StockMovement]:
    qty = _q(quantity)
    consumed = _fifo_consume(branch=branch, chemical=chemical, quantity=qty)
    _apply_balance_delta(
        branch=branch,
        item_type=StockMovement.ItemType.CHEMICAL,
        delta=-qty,
        chemical=chemical,
    )
    movements = []
    for lot, take, unit_cost in consumed:
        movements.append(
            StockMovement.objects.create(
                movement_type=StockMovement.MovementType.ISSUE,
                item_type=StockMovement.ItemType.CHEMICAL,
                branch=branch,
                chemical=chemical,
                lot=lot if isinstance(lot, StockLot) else None,
                technician=technician,
                jobcard=jobcard,
                quantity=take,
                unit_cost=unit_cost,
                line_cost=_money(take * unit_cost),
                movement_date=movement_date or timezone.localdate(),
                reference=reference,
                remarks=remarks,
                created_by=user,
            )
        )
    return movements


@transaction.atomic
def return_stock(
    *,
    branch: Branch,
    chemical: Chemical,
    quantity,
    technician: Technician | None = None,
    unit_cost=0,
    movement_date=None,
    reference: str = '',
    remarks: str = '',
    user=None,
) -> StockMovement:
    qty = _q(quantity)
    if qty <= 0:
        raise ValidationError('Return quantity must be positive.')
    cost = _cost4(unit_cost)
    lot = StockLot.objects.create(
        branch=branch,
        item_type=StockLot.ItemType.CHEMICAL,
        chemical=chemical,
        unit_cost=cost,
        qty_received=qty,
        qty_remaining=qty,
        purchased_at=movement_date or timezone.localdate(),
        batch_no='RETURN',
    )
    _apply_balance_delta(
        branch=branch,
        item_type=StockMovement.ItemType.CHEMICAL,
        delta=qty,
        chemical=chemical,
        allow_negative=True,
    )
    return StockMovement.objects.create(
        movement_type=StockMovement.MovementType.RETURN,
        item_type=StockMovement.ItemType.CHEMICAL,
        branch=branch,
        chemical=chemical,
        lot=lot,
        technician=technician,
        quantity=qty,
        unit_cost=cost,
        line_cost=_money(qty * cost),
        movement_date=movement_date or timezone.localdate(),
        reference=reference,
        remarks=remarks,
        created_by=user,
    )


@transaction.atomic
def transfer_stock(
    *,
    from_branch: Branch,
    to_branch: Branch,
    item_type: str,
    quantity,
    chemical: Chemical | None = None,
    equipment: Equipment | None = None,
    movement_date=None,
    reference: str = '',
    remarks: str = '',
    user=None,
) -> tuple[StockMovement, StockMovement]:
    if from_branch.id == to_branch.id:
        raise ValidationError('Cannot transfer to the same branch.')
    qty = _q(quantity)
    if qty <= 0:
        raise ValidationError('Transfer quantity must be positive.')
    unit_cost = Decimal('0')
    if item_type == StockMovement.ItemType.CHEMICAL and chemical:
        consumed = _fifo_consume(branch=from_branch, chemical=chemical, quantity=qty)
        unit_cost = consumed[0][2] if consumed else Decimal('0')
        total_cost = sum((_money(t * c) for _, t, c in consumed), Decimal('0'))
        avg = _cost4(total_cost / qty) if qty else Decimal('0')
        unit_cost = avg
        dest_lot = StockLot.objects.create(
            branch=to_branch,
            item_type=item_type,
            chemical=chemical,
            unit_cost=unit_cost,
            qty_received=qty,
            qty_remaining=qty,
            purchased_at=movement_date or timezone.localdate(),
            batch_no=f'TRF-{from_branch.code}',
        )
    else:
        dest_lot = StockLot.objects.create(
            branch=to_branch,
            item_type=item_type,
            equipment=equipment,
            unit_cost=unit_cost,
            qty_received=qty,
            qty_remaining=qty,
            purchased_at=movement_date or timezone.localdate(),
            batch_no=f'TRF-{from_branch.code}',
        )
    _apply_balance_delta(
        branch=from_branch, item_type=item_type, delta=-qty,
        chemical=chemical, equipment=equipment,
    )
    _apply_balance_delta(
        branch=to_branch, item_type=item_type, delta=qty,
        chemical=chemical, equipment=equipment, allow_negative=True,
    )
    date = movement_date or timezone.localdate()
    out_mv = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.TRANSFER_OUT,
        item_type=item_type,
        branch=from_branch,
        to_branch=to_branch,
        chemical=chemical,
        equipment=equipment,
        quantity=qty,
        unit_cost=unit_cost,
        line_cost=_money(qty * unit_cost),
        movement_date=date,
        reference=reference,
        remarks=remarks,
        created_by=user,
    )
    in_mv = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.TRANSFER_IN,
        item_type=item_type,
        branch=to_branch,
        to_branch=from_branch,
        chemical=chemical,
        equipment=equipment,
        lot=dest_lot,
        quantity=qty,
        unit_cost=unit_cost,
        line_cost=_money(qty * unit_cost),
        movement_date=date,
        reference=reference,
        remarks=remarks,
        created_by=user,
    )
    return out_mv, in_mv


@transaction.atomic
def record_chemical_usage(
    *,
    job: JobCard,
    chemical: Chemical,
    quantity_ml,
    source: str = ChemicalUsage.Source.CRM,
    user=None,
    remarks: str = '',
    deduct_stock: bool = True,
) -> ChemicalUsage:
    from accounts.services.profit import recalculate_booking_cost

    qty = _q(quantity_ml)
    if qty <= 0:
        raise ValidationError('Usage quantity must be positive.')
    branch = resolve_branch_for_job(job)
    if not branch:
        raise ValidationError('No branch configured for this booking city.')

    line_cost = Decimal('0')
    unit_cost = Decimal('0')
    lot = None
    if deduct_stock:
        movements = issue_stock(
            branch=branch,
            chemical=chemical,
            quantity=qty,
            technician=job.technician,
            jobcard=job,
            remarks=remarks or f'Usage on job #{job.id}',
            user=user,
        )
        total = sum((m.line_cost for m in movements), Decimal('0'))
        line_cost = _money(total)
        unit_cost = _cost4(line_cost / qty) if qty else Decimal('0')
        lot = next((m.lot for m in movements if m.lot_id), None)
        for m in movements:
            m.movement_type = StockMovement.MovementType.USAGE
            m.save(update_fields=['movement_type', 'updated_at'])
    else:
        last = (
            StockLot.objects.filter(chemical=chemical)
            .order_by('-purchased_at', '-id')
            .first()
        )
        unit_cost = _cost4(last.unit_cost) if last else Decimal('0')
        line_cost = _money(qty * unit_cost)

    usage = ChemicalUsage.objects.create(
        jobcard=job,
        branch=branch,
        chemical=chemical,
        lot=lot,
        quantity_ml=qty,
        unit_cost_snapshot=unit_cost,
        line_cost=line_cost,
        source=source,
        created_by=user,
        remarks=remarks,
    )
    if job.status == JobCard.JobStatus.DONE:
        recalculate_booking_cost(job)
    return usage
