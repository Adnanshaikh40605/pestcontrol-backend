from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import decorators, filters, permissions, response, status, viewsets
from rest_framework.permissions import SAFE_METHODS

from .models import (
    PricingRate,
    PricingRateAuditAction,
    PricingRateAuditLog,
    PricingRegion,
)
from .permissions import IsCRMOperationalUser, IsPricingAdmin
from .pricing_master_serializers import (
    PricingRateAuditLogSerializer,
    PricingRateSerializer,
    PricingRegionSerializer,
)
from .views import LargePagination


def _log_pricing_change(
    *,
    rate: PricingRate | None,
    action: str,
    user,
    old_amount: Decimal | None = None,
    new_amount: Decimal | None = None,
    change_note: str = '',
):
    if not rate:
        return
    PricingRateAuditLog.objects.create(
        rate=rate,
        region_slug=rate.region.slug,
        service_package=rate.service_package,
        plan_type=rate.plan_type,
        area_key=rate.area_key,
        property_category=rate.property_category,
        old_amount=old_amount,
        new_amount=new_amount,
        action=action,
        changed_by=user if user and user.is_authenticated else None,
        change_note=change_note,
    )


class PricingRegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PricingRegion.objects.filter(is_active=True).select_related('city')
    serializer_class = PricingRegionSerializer
    permission_classes = [IsCRMOperationalUser]
    pagination_class = LargePagination
    search_fields = ['name', 'slug']
    filterset_fields = ['is_default', 'city']


class PricingRateViewSet(viewsets.ModelViewSet):
    queryset = PricingRate.objects.select_related('region', 'updated_by').order_by(
        'region__name', 'service_package', 'plan_type', 'area_key',
    )
    serializer_class = PricingRateSerializer
    pagination_class = LargePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['service_package', 'area_key', 'plan_type', 'region__name', 'region__slug']
    filterset_fields = ['region', 'service_package', 'plan_type', 'property_category', 'is_active']
    ordering_fields = ['service_package', 'plan_type', 'area_key', 'amount', 'updated_at', 'created_at']
    ordering = ['region__name', 'service_package', 'plan_type', 'area_key']

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsCRMOperationalUser()]
        return [IsPricingAdmin()]

    def perform_create(self, serializer):
        rate = serializer.save(updated_by=self.request.user)
        _log_pricing_change(
            rate=rate,
            action=PricingRateAuditAction.CREATE,
            user=self.request.user,
            new_amount=rate.amount,
            change_note='Created via Pricing Master',
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        old_amount = instance.amount
        rate = serializer.save(updated_by=self.request.user)
        action = PricingRateAuditAction.UPDATE
        if 'is_active' in serializer.validated_data:
            if rate.is_active and not instance.is_active:
                action = PricingRateAuditAction.ACTIVATE
            elif not rate.is_active and instance.is_active:
                action = PricingRateAuditAction.DEACTIVATE
        if old_amount != rate.amount or action != PricingRateAuditAction.UPDATE:
            _log_pricing_change(
                rate=rate,
                action=action,
                user=self.request.user,
                old_amount=old_amount,
                new_amount=rate.amount,
                change_note='Updated via Pricing Master',
            )

    def perform_destroy(self, instance):
        _log_pricing_change(
            rate=instance,
            action=PricingRateAuditAction.DEACTIVATE,
            user=self.request.user,
            old_amount=instance.amount,
            new_amount=instance.amount,
            change_note='Soft-deactivated via Pricing Master',
        )
        instance.is_active = False
        instance.updated_by = self.request.user
        instance.save(update_fields=['is_active', 'updated_by', 'updated_at'])


class PricingRateAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PricingRateAuditLog.objects.select_related('changed_by', 'rate').order_by('-created_at')
    serializer_class = PricingRateAuditLogSerializer
    permission_classes = [IsPricingAdmin]
    pagination_class = LargePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['service_package', 'area_key', 'region_slug', 'change_note']
    filterset_fields = ['region_slug', 'service_package', 'action']
    ordering = ['-created_at']
