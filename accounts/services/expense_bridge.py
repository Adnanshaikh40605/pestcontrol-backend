"""Bridge staff_tracking ExpenseClaim → accounts ExpenseEntry."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from accounts.models import ExpenseCategory, ExpenseEntry
from accounts.services.profit import recalculate_booking_cost
from accounts.services.stock import resolve_branch_for_job


@transaction.atomic
def bridge_expense_claim(claim) -> ExpenseEntry | None:
    """
    Create or update a posted ExpenseEntry from an approved/paid ExpenseClaim.
    Idempotent on source_expense_claim_id.
    """
    status = getattr(claim, 'status', '') or ''
    if status not in ('approved', 'paid'):
        return None

    existing = ExpenseEntry.objects.filter(source_expense_claim_id=claim.id).first()
    category_name = getattr(getattr(claim, 'category', None), 'name', None) or 'Other Expenses'
    category, _ = ExpenseCategory.objects.get_or_create(
        group=ExpenseCategory.Group.TECHNICIAN,
        name=category_name[:120],
        defaults={'is_overhead': False, 'is_active': True},
    )

    job = getattr(claim, 'jobcard', None)
    branch = resolve_branch_for_job(job) if job else None
    if not branch:
        from accounts.models import Branch

        branch = Branch.objects.filter(is_active=True).order_by('id').first()
    if not branch:
        return None

    amount = Decimal(str(getattr(claim, 'amount', 0) or 0))
    gst = Decimal(str(getattr(claim, 'gst_amount', 0) or 0))
    defaults = {
        'entry_date': getattr(claim, 'expense_date', None) or getattr(claim, 'created_at', None),
        'branch': branch,
        'category': category,
        'technician_id': getattr(claim, 'technician_id', None),
        'jobcard': job,
        'amount': amount,
        'gst_amount': gst,
        'payment_mode': ExpenseEntry.PaymentMode.OTHER,
        'remarks': (getattr(claim, 'notes', '') or '')[:2000],
        'status': ExpenseEntry.Status.POSTED,
    }
    if hasattr(defaults['entry_date'], 'date'):
        defaults['entry_date'] = defaults['entry_date'].date()

    if existing:
        for key, value in defaults.items():
            setattr(existing, key, value)
        existing.save()
        entry = existing
    else:
        entry = ExpenseEntry.objects.create(source_expense_claim_id=claim.id, **defaults)

    if job and getattr(job, 'status', None) == 'Done':
        recalculate_booking_cost(job)
    return entry
