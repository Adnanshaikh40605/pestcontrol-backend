from rest_framework import serializers

from accounts.models import (
    AccountsAlert,
    BookingCostSnapshot,
    Branch,
    BranchCityMap,
    Chemical,
    ChemicalUsage,
    DailyBranchPnL,
    Equipment,
    ExpenseCategory,
    ExpenseEntry,
    MonthlyBranchPnL,
    MonthlyOverheadRate,
    StockBalance,
    StockLot,
    StockMovement,
    Supplier,
)


class BranchSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = Branch
        fields = (
            'id', 'name', 'code', 'city', 'city_name', 'is_active', 'notes',
            'created_at', 'updated_at',
        )


class BranchCityMapSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = BranchCityMap
        fields = ('id', 'branch', 'branch_name', 'city', 'city_name', 'created_at')


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = (
            'id', 'name', 'mobile', 'email', 'gstin', 'address',
            'is_active', 'notes', 'created_at', 'updated_at',
        )


class ChemicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chemical
        fields = (
            'id', 'name', 'sku', 'unit', 'reorder_level', 'gst_percent',
            'is_active', 'notes', 'created_at', 'updated_at',
        )


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = (
            'id', 'name', 'sku', 'reorder_level', 'is_active', 'notes',
            'created_at', 'updated_at',
        )


class StockLotSerializer(serializers.ModelSerializer):
    chemical_name = serializers.CharField(source='chemical.name', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = StockLot
        fields = (
            'id', 'branch', 'branch_name', 'item_type', 'chemical', 'chemical_name',
            'equipment', 'equipment_name', 'supplier', 'batch_no', 'expiry_date',
            'unit_cost', 'qty_received', 'qty_remaining', 'purchased_at',
        )


class StockBalanceSerializer(serializers.ModelSerializer):
    chemical_name = serializers.CharField(source='chemical.name', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    reorder_level = serializers.SerializerMethodField()
    is_low = serializers.SerializerMethodField()

    class Meta:
        model = StockBalance
        fields = (
            'id', 'branch', 'branch_name', 'item_type', 'chemical', 'chemical_name',
            'equipment', 'equipment_name', 'quantity', 'reorder_level', 'is_low',
        )

    def get_reorder_level(self, obj):
        if obj.chemical_id:
            return obj.chemical.reorder_level
        if obj.equipment_id:
            return obj.equipment.reorder_level
        return 0

    def get_is_low(self, obj):
        reorder = self.get_reorder_level(obj) or 0
        return obj.quantity <= reorder


class StockMovementSerializer(serializers.ModelSerializer):
    chemical_name = serializers.CharField(source='chemical.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            'id', 'movement_type', 'item_type', 'branch', 'branch_name', 'to_branch',
            'chemical', 'chemical_name', 'equipment', 'lot', 'supplier', 'supplier_name',
            'technician', 'jobcard', 'quantity', 'unit_cost', 'line_cost',
            'movement_date', 'reference', 'remarks', 'payment_pending', 'created_at',
        )
        read_only_fields = fields


class PurchaseSerializer(serializers.Serializer):
    branch_id = serializers.IntegerField()
    item_type = serializers.ChoiceField(choices=['chemical', 'equipment'])
    chemical_id = serializers.IntegerField(required=False, allow_null=True)
    equipment_id = serializers.IntegerField(required=False, allow_null=True)
    supplier_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=4)
    batch_no = serializers.CharField(required=False, allow_blank=True, default='')
    expiry_date = serializers.DateField(required=False, allow_null=True)
    movement_date = serializers.DateField(required=False, allow_null=True)
    reference = serializers.CharField(required=False, allow_blank=True, default='')
    remarks = serializers.CharField(required=False, allow_blank=True, default='')
    payment_pending = serializers.BooleanField(required=False, default=False)


class AdjustSerializer(serializers.Serializer):
    branch_id = serializers.IntegerField()
    item_type = serializers.ChoiceField(choices=['chemical', 'equipment'])
    chemical_id = serializers.IntegerField(required=False, allow_null=True)
    equipment_id = serializers.IntegerField(required=False, allow_null=True)
    quantity_delta = serializers.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, default=0)
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class IssueSerializer(serializers.Serializer):
    branch_id = serializers.IntegerField()
    chemical_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    technician_id = serializers.IntegerField(required=False, allow_null=True)
    jobcard_id = serializers.IntegerField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class TransferSerializer(serializers.Serializer):
    from_branch_id = serializers.IntegerField()
    to_branch_id = serializers.IntegerField()
    item_type = serializers.ChoiceField(choices=['chemical', 'equipment'])
    chemical_id = serializers.IntegerField(required=False, allow_null=True)
    equipment_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class ChemicalUsageSerializer(serializers.ModelSerializer):
    chemical_name = serializers.CharField(source='chemical.name', read_only=True)

    class Meta:
        model = ChemicalUsage
        fields = (
            'id', 'jobcard', 'branch', 'chemical', 'chemical_name', 'lot',
            'quantity_ml', 'unit_cost_snapshot', 'line_cost', 'source', 'remarks',
            'created_at',
        )
        read_only_fields = (
            'branch', 'lot', 'unit_cost_snapshot', 'line_cost', 'created_at',
        )


class ChemicalUsageCreateSerializer(serializers.Serializer):
    jobcard_id = serializers.IntegerField()
    chemical_id = serializers.IntegerField()
    quantity_ml = serializers.DecimalField(max_digits=14, decimal_places=3)
    source = serializers.ChoiceField(choices=['crm', 'app'], default='crm')
    remarks = serializers.CharField(required=False, allow_blank=True, default='')
    deduct_stock = serializers.BooleanField(default=True)


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ('id', 'group', 'name', 'is_active', 'is_overhead')


class ExpenseEntrySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_group = serializers.CharField(source='category.group', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ExpenseEntry
        fields = (
            'id', 'entry_date', 'branch', 'branch_name', 'category', 'category_name',
            'category_group', 'vendor_name', 'supplier', 'technician', 'jobcard',
            'amount', 'gst_amount', 'total_amount', 'payment_mode', 'bill', 'remarks',
            'status', 'source_expense_claim_id', 'created_at', 'updated_at',
        )


class BookingCostSnapshotSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    customer_name = serializers.CharField(source='jobcard.client_name', read_only=True)
    service_type = serializers.CharField(source='jobcard.service_type', read_only=True)
    booking_id = serializers.IntegerField(source='jobcard_id', read_only=True)

    class Meta:
        model = BookingCostSnapshot
        fields = (
            'id', 'booking_id', 'jobcard', 'branch', 'branch_name', 'booking_date',
            'customer_name', 'service_type', 'booking_amount', 'visit_revenue',
            'chemical_cost', 'direct_expense_cost', 'technician_cost', 'company_share',
            'overhead_cost', 'total_cost', 'gross_profit', 'company_net_profit',
            'gross_margin_percent', 'company_margin_percent', 'cost_percent',
            'computed_at',
        )


class DailyBranchPnLSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = DailyBranchPnL
        fields = '__all__'


class MonthlyBranchPnLSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = MonthlyBranchPnL
        fields = '__all__'


class MonthlyOverheadRateSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = MonthlyOverheadRate
        fields = '__all__'


class AccountsAlertSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = AccountsAlert
        fields = (
            'id', 'alert_type', 'severity', 'branch', 'branch_name', 'title',
            'message', 'payload', 'is_read', 'is_resolved', 'created_at',
        )
