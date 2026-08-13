from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import (
    AccountsAlertViewSet,
    AccountsDashboardView,
    AccountsExportView,
    AccountsRebuildView,
    BookingCostSnapshotViewSet,
    BranchCityMapViewSet,
    BranchViewSet,
    ChemicalUsageViewSet,
    ChemicalViewSet,
    DailyPnLViewSet,
    EquipmentViewSet,
    ExpenseCategoryViewSet,
    ExpenseEntryViewSet,
    MonthlyPnLViewSet,
    OverheadViewSet,
    StockBalanceViewSet,
    StockLotViewSet,
    StockMovementViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register(r'branches', BranchViewSet)
router.register(r'branch-city-maps', BranchCityMapViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'chemicals', ChemicalViewSet)
router.register(r'equipment', EquipmentViewSet)
router.register(r'stock-balances', StockBalanceViewSet)
router.register(r'stock-lots', StockLotViewSet)
router.register(r'stock-movements', StockMovementViewSet, basename='stock-movements')
router.register(r'chemical-usages', ChemicalUsageViewSet)
router.register(r'expense-categories', ExpenseCategoryViewSet)
router.register(r'expenses', ExpenseEntryViewSet)
router.register(r'booking-costs', BookingCostSnapshotViewSet, basename='booking-costs')
router.register(r'daily-pnl', DailyPnLViewSet)
router.register(r'monthly-pnl', MonthlyPnLViewSet)
router.register(r'overhead', OverheadViewSet, basename='overhead')
router.register(r'alerts', AccountsAlertViewSet)

urlpatterns = [
    path('dashboard/', AccountsDashboardView.as_view(), name='accounts-dashboard'),
    path('rebuild-pnl/', AccountsRebuildView.as_view(), name='accounts-rebuild-pnl'),
    path('export/', AccountsExportView.as_view(), name='accounts-export'),
    path('', include(router.urls)),
]
