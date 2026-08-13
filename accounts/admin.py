from django.contrib import admin

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


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'is_active')
    search_fields = ('name', 'code')


admin.site.register(BranchCityMap)
admin.site.register(Supplier)
admin.site.register(Chemical)
admin.site.register(Equipment)
admin.site.register(StockLot)
admin.site.register(StockBalance)
admin.site.register(StockMovement)
admin.site.register(ChemicalUsage)
admin.site.register(ExpenseCategory)
admin.site.register(ExpenseEntry)
admin.site.register(MonthlyOverheadRate)
admin.site.register(BookingCostSnapshot)
admin.site.register(DailyBranchPnL)
admin.site.register(MonthlyBranchPnL)
admin.site.register(AccountsAlert)
