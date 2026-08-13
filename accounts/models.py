"""Accounts Management — inventory, expenses, booking profit, P&L rollups."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel, City, JobCard, Technician


def _local_today():
    return timezone.localdate()


class Branch(BaseModel):
    name = models.CharField(max_length=120, unique=True, db_index=True)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return self.name


class BranchCityMap(BaseModel):
    """Maps a master city to a default operating branch."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='city_maps')
    city = models.OneToOneField(City, on_delete=models.CASCADE, related_name='branch_map')

    class Meta:
        verbose_name = 'Branch city map'
        verbose_name_plural = 'Branch city maps'

    def __str__(self):
        return f'{self.city} → {self.branch}'


class Supplier(BaseModel):
    name = models.CharField(max_length=200, db_index=True)
    mobile = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    gstin = models.CharField(max_length=30, blank=True, default='')
    address = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Chemical(BaseModel):
    class Unit(models.TextChoices):
        ML = 'ml', 'Millilitre'
        L = 'L', 'Litre'
        G = 'g', 'Gram'
        KG = 'kg', 'Kilogram'
        PCS = 'pcs', 'Pieces'

    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=60, blank=True, default='', db_index=True)
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.ML)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0'))
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Equipment(BaseModel):
    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=60, blank=True, default='', db_index=True)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0'))
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Equipment'

    def __str__(self):
        return self.name


class StockLot(BaseModel):
    """Purchase lot for FIFO costing and expiry tracking."""

    class ItemType(models.TextChoices):
        CHEMICAL = 'chemical', 'Chemical'
        EQUIPMENT = 'equipment', 'Equipment'

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stock_lots')
    item_type = models.CharField(max_length=20, choices=ItemType.choices, db_index=True)
    chemical = models.ForeignKey(
        Chemical, on_delete=models.CASCADE, null=True, blank=True, related_name='lots',
    )
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, null=True, blank=True, related_name='lots',
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='lots',
    )
    batch_no = models.CharField(max_length=80, blank=True, default='')
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    qty_received = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal('0'))
    qty_remaining = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal('0'))
    purchased_at = models.DateField(default=_local_today, db_index=True)

    class Meta:
        ordering = ['expiry_date', 'purchased_at', 'id']
        indexes = [
            models.Index(fields=['branch', 'item_type', 'chemical']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self):
        label = self.chemical or self.equipment
        return f'{label} lot#{self.pk} ({self.qty_remaining})'


class StockBalance(BaseModel):
    """Cached on-hand qty per branch + item (updated by stock service)."""

    class ItemType(models.TextChoices):
        CHEMICAL = 'chemical', 'Chemical'
        EQUIPMENT = 'equipment', 'Equipment'

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stock_balances')
    item_type = models.CharField(max_length=20, choices=ItemType.choices, db_index=True)
    chemical = models.ForeignKey(
        Chemical, on_delete=models.CASCADE, null=True, blank=True, related_name='balances',
    )
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, null=True, blank=True, related_name='balances',
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal('0'))

    class Meta:
        ordering = ['branch_id', 'item_type', 'id']
        indexes = [
            models.Index(fields=['branch', 'item_type']),
            models.Index(fields=['branch', 'chemical']),
            models.Index(fields=['branch', 'equipment']),
        ]

    def __str__(self):
        return f'{self.branch} {self.chemical or self.equipment}: {self.quantity}'


class StockMovement(BaseModel):
    class MovementType(models.TextChoices):
        PURCHASE = 'purchase', 'Purchase'
        PURCHASE_RETURN = 'purchase_return', 'Purchase Return'
        ADJUSTMENT = 'adjustment', 'Stock Adjustment'
        ISSUE = 'issue', 'Issue to Technician'
        RETURN = 'return', 'Chemical Return'
        TRANSFER_OUT = 'transfer_out', 'Branch Transfer Out'
        TRANSFER_IN = 'transfer_in', 'Branch Transfer In'
        USAGE = 'usage', 'Job Usage COGS'

    class ItemType(models.TextChoices):
        CHEMICAL = 'chemical', 'Chemical'
        EQUIPMENT = 'equipment', 'Equipment'

    movement_type = models.CharField(max_length=30, choices=MovementType.choices, db_index=True)
    item_type = models.CharField(max_length=20, choices=ItemType.choices, db_index=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stock_movements')
    to_branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transfers_in',
    )
    chemical = models.ForeignKey(
        Chemical, on_delete=models.CASCADE, null=True, blank=True, related_name='movements',
    )
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, null=True, blank=True, related_name='movements',
    )
    lot = models.ForeignKey(
        StockLot, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements',
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements',
    )
    technician = models.ForeignKey(
        Technician, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_issues',
    )
    jobcard = models.ForeignKey(
        JobCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements',
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    line_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    movement_date = models.DateField(default=_local_today, db_index=True)
    reference = models.CharField(max_length=120, blank=True, default='')
    remarks = models.TextField(blank=True, default='')
    payment_pending = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements_created',
    )

    class Meta:
        ordering = ['-movement_date', '-id']
        indexes = [
            models.Index(fields=['branch', 'movement_date']),
            models.Index(fields=['jobcard']),
            models.Index(fields=['chemical', 'movement_date']),
        ]

    def __str__(self):
        return f'{self.movement_type} {self.quantity} @ {self.branch}'


class ChemicalUsage(BaseModel):
    class Source(models.TextChoices):
        CRM = 'crm', 'CRM'
        APP = 'app', 'Partner App'

    jobcard = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='chemical_usages')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='chemical_usages')
    chemical = models.ForeignKey(Chemical, on_delete=models.PROTECT, related_name='usages')
    lot = models.ForeignKey(
        StockLot, on_delete=models.SET_NULL, null=True, blank=True, related_name='usages',
    )
    quantity_ml = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost_snapshot = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    line_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.CRM)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chemical_usages_created',
    )
    remarks = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-id']
        indexes = [models.Index(fields=['jobcard']), models.Index(fields=['chemical'])]

    def __str__(self):
        return f'Job#{self.jobcard_id} {self.chemical} {self.quantity_ml}ml'


class ExpenseCategory(BaseModel):
    class Group(models.TextChoices):
        OFFICE = 'office', 'Office'
        MARKETING = 'marketing', 'Marketing'
        TECHNICIAN = 'technician', 'Technician'
        PURCHASE = 'purchase', 'Purchase'

    group = models.CharField(max_length=20, choices=Group.choices, db_index=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    is_overhead = models.BooleanField(
        default=False,
        help_text='Include in monthly office overhead allocation when True.',
    )

    class Meta:
        unique_together = ('group', 'name')
        ordering = ['group', 'name']
        verbose_name_plural = 'Expense categories'

    def __str__(self):
        return f'{self.get_group_display()} / {self.name}'


class ExpenseEntry(BaseModel):
    class PaymentMode(models.TextChoices):
        CASH = 'cash', 'Cash'
        ONLINE = 'online', 'Online'
        UPI = 'upi', 'UPI'
        CARD = 'card', 'Card'
        CHEQUE = 'cheque', 'Cheque'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        VOID = 'void', 'Void'

    entry_date = models.DateField(default=_local_today, db_index=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='entries')
    vendor_name = models.CharField(max_length=200, blank=True, default='')
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses',
    )
    technician = models.ForeignKey(
        Technician, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_expenses',
    )
    jobcard = models.ForeignKey(
        JobCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_expenses',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    payment_mode = models.CharField(
        max_length=20, choices=PaymentMode.choices, default=PaymentMode.CASH,
    )
    bill = models.FileField(upload_to='accounts/expense_bills/%Y/%m/', blank=True, null=True)
    remarks = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.POSTED, db_index=True,
    )
    source_expense_claim_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True,
        help_text='staff_tracking.ExpenseClaim id when bridged',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expense_entries_created',
    )

    class Meta:
        ordering = ['-entry_date', '-id']
        indexes = [
            models.Index(fields=['branch', 'entry_date']),
            models.Index(fields=['jobcard']),
            models.Index(fields=['status', 'entry_date']),
        ]
        verbose_name_plural = 'Expense entries'

    @property
    def total_amount(self) -> Decimal:
        return (self.amount or Decimal('0')) + (self.gst_amount or Decimal('0'))

    def __str__(self):
        return f'{self.entry_date} {self.category} ₹{self.amount}'


class MonthlyOverheadRate(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='overhead_rates')
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    total_overhead = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    completed_bookings = models.PositiveIntegerField(default=0)
    overhead_per_booking = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('branch', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f'{self.branch} {self.year}-{self.month:02d}: ₹{self.overhead_per_booking}'


class BookingCostSnapshot(BaseModel):
    jobcard = models.OneToOneField(
        JobCard, on_delete=models.CASCADE, related_name='cost_snapshot',
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='booking_snapshots',
    )
    booking_date = models.DateField(db_index=True)
    booking_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    visit_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    chemical_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    direct_expense_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    technician_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    company_share = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    overhead_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    company_net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    gross_margin_percent = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    company_margin_percent = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    cost_percent = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-booking_date', '-id']
        indexes = [
            models.Index(fields=['branch', 'booking_date']),
            models.Index(fields=['booking_date']),
        ]

    def __str__(self):
        return f'Snapshot Job#{self.jobcard_id} GP ₹{self.gross_profit}'


class DailyBranchPnL(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='daily_pnl')
    date = models.DateField(db_index=True)
    sales = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    chemical_cogs = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    direct_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    technician_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    overhead = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    office_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    gross_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    company_net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    booking_count = models.PositiveIntegerField(default=0)
    avg_cost_per_booking = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    avg_profit_per_booking = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    inventory_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))

    class Meta:
        unique_together = ('branch', 'date')
        ordering = ['-date']
        verbose_name = 'Daily branch P&L'
        verbose_name_plural = 'Daily branch P&L'

    def __str__(self):
        return f'{self.branch} {self.date}'


class MonthlyBranchPnL(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='monthly_pnl')
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    sales = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    chemical_cogs = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    direct_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    technician_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    overhead = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    office_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    gross_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    company_net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    booking_count = models.PositiveIntegerField(default=0)
    avg_cost_per_booking = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    avg_profit_per_booking = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    inventory_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    chemical_consumption = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal('0'))

    class Meta:
        unique_together = ('branch', 'year', 'month')
        ordering = ['-year', '-month']
        verbose_name = 'Monthly branch P&L'
        verbose_name_plural = 'Monthly branch P&L'

    def __str__(self):
        return f'{self.branch} {self.year}-{self.month:02d}'


class AccountsAlert(BaseModel):
    class AlertType(models.TextChoices):
        LOW_STOCK = 'low_stock', 'Low Stock'
        EXPIRY = 'expiry', 'Chemical Expiry'
        SUPPLIER_PAYMENT = 'supplier_payment', 'Pending Supplier Payment'
        HIGH_EXPENSE = 'high_expense', 'High Expense'
        EXCESS_CHEMICAL = 'excess_chemical', 'Excess Chemical Consumption'
        DAILY_PROFIT = 'daily_profit', 'Daily Profit Summary'
        MONTHLY_PROFIT = 'monthly_profit', 'Monthly Profit Summary'

    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        CRITICAL = 'critical', 'Critical'

    alert_type = models.CharField(max_length=30, choices=AlertType.choices, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts',
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_resolved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['alert_type', 'is_resolved'])]

    def __str__(self):
        return self.title
