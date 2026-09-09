from decimal import Decimal

import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, response, status, viewsets
from rest_framework.decorators import action

from .models import (
    PricingPropertyCategory,
    PricingRate,
    PricingRateAuditAction,
    PricingRateAuditLog,
    PricingRegion,
)
from .permissions import IsPricingAdmin
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
    permission_classes = [IsPricingAdmin]
    pagination_class = LargePagination
    search_fields = ['name', 'slug']
    filterset_fields = ['is_default', 'city']


class PlanTypeInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    """Comma-separated `plan_type` list."""


class PricingRateFilterSet(django_filters.FilterSet):
    """
    Adds `plan_type__in` on top of the existing exact-match filters.

    A single plan tab in the CRM covers a whole family — "AMC" means the three
    AMC plans, "Monthly / Recurring" means seven visit-frequency plans — and
    exact match alone would have forced one request per plan or, worse, made the
    UI download every city's rates and hide rows locally.
    """

    plan_type__in = PlanTypeInFilter(field_name='plan_type', lookup_expr='in')

    class Meta:
        model = PricingRate
        fields = ['region', 'service_package', 'plan_type', 'property_category', 'is_active']


class PricingRateViewSet(viewsets.ModelViewSet):
    queryset = PricingRate.objects.select_related('region', 'updated_by').order_by(
        'region__name', 'service_package', 'plan_type', 'area_key',
    )
    serializer_class = PricingRateSerializer
    pagination_class = LargePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['service_package', 'area_key', 'plan_type', 'region__name', 'region__slug']
    filterset_class = PricingRateFilterSet
    # `region__name` was missing, so the CRM's ordering request was silently
    # stripped of its first term and the list came back ungrouped.
    ordering_fields = [
        'region__name', 'service_package', 'plan_type', 'area_key',
        'amount', 'updated_at', 'created_at',
    ]
    ordering = ['region__name', 'service_package', 'plan_type', 'area_key']

    permission_classes = [IsPricingAdmin]

    @action(detail=False, methods=['get'], url_path='options')
    def options_list(self, request):
        """
        Distinct values already stored, for the Add/Edit Rate dropdowns and the
        CRM's plan tabs.

        The form used to hard-code four services and five plan types, so most
        of the imported rate chart was impossible to select and an existing
        rate's plan showed the wrong option. Driving the selects from the data
        keeps them honest without letting staff free-type a new spelling of an
        existing service (which is how duplicate services appeared before).

        `?region=<id>` scopes the values to one city and `?plan_type__in=a,b`
        narrows them further. The CRM's tabs use both so it never offers a
        city a plan, or a plan a service, with no rates behind it.
        """
        base = PricingRate.objects.all()
        region_id = str(request.query_params.get('region', '')).strip()
        if region_id.isdigit():
            base = base.filter(region_id=int(region_id))

        plans = [
            plan.strip()
            for plan in str(request.query_params.get('plan_type__in', '')).split(',')
            if plan.strip()
        ]
        if plans:
            base = base.filter(plan_type__in=plans)

        def distinct(field: str) -> list[str]:
            values = (
                base.exclude(**{f'{field}': ''})
                .values_list(field, flat=True)
                .distinct()
            )
            return sorted({v for v in values if v})

        return response.Response({
            'service_packages': distinct('service_package'),
            'plan_types': distinct('plan_type'),
            'billing_bases': distinct('billing_basis'),
            'property_categories': [
                {'value': value, 'label': label}
                for value, label in PricingPropertyCategory.choices
            ],
        })

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
        old_gst = instance.gst_percent
        old_includes = instance.price_includes_gst
        old_active = instance.is_active
        rate = serializer.save(updated_by=self.request.user)
        action = PricingRateAuditAction.UPDATE
        if 'is_active' in serializer.validated_data:
            if rate.is_active and not old_active:
                action = PricingRateAuditAction.ACTIVATE
            elif not rate.is_active and old_active:
                action = PricingRateAuditAction.DEACTIVATE
        gst_changed = (
            old_gst != rate.gst_percent
            or old_includes != rate.price_includes_gst
        )
        if old_amount != rate.amount or action != PricingRateAuditAction.UPDATE or gst_changed:
            note = 'Updated via Pricing Master'
            if gst_changed:
                note = (
                    f'Updated via Pricing Master '
                    f'(GST {old_gst}%→{rate.gst_percent}%, '
                    f'includes={old_includes}→{rate.price_includes_gst})'
                )
            _log_pricing_change(
                rate=rate,
                action=action,
                user=self.request.user,
                old_amount=old_amount,
                new_amount=rate.amount,
                change_note=note,
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
