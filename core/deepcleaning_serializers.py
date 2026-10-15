"""Serializers for DeepCleaning99 inquiries (isolated from pest Website Leads)."""

from __future__ import annotations

from rest_framework import serializers

from decimal import Decimal

from .models import DeepCleaningInquiry, DeepCleaningInquiryRemark, DeepCleaningRate
from .serializers import _resolve_latest_remark, _serialize_latest_remark


def _user_display(user) -> str:
    if not user:
        return 'System'
    return user.get_full_name() or user.username


class DeepCleaningInquiryRemarkSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DeepCleaningInquiryRemark
        fields = [
            'id', 'inquiry', 'remark', 'remark_type',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'inquiry', 'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]

    def get_created_by_name(self, obj):
        return _user_display(obj.created_by)


class DeepCleaningInquirySerializer(serializers.ModelSerializer):
    latest_remark = serializers.SerializerMethodField()
    remark = serializers.SerializerMethodField()
    remark_count = serializers.IntegerField(read_only=True, required=False)
    needs_comment_update = serializers.BooleanField(read_only=True, required=False)
    comment_status = serializers.SerializerMethodField()
    preferred_date_display = serializers.SerializerMethodField()
    received_display = serializers.SerializerMethodField()

    class Meta:
        model = DeepCleaningInquiry
        fields = [
            'id', 'name', 'mobile', 'email',
            'city', 'area', 'address',
            'segment', 'service', 'package_name', 'package_id',
            'quantity', 'unit', 'plan',
            'property_size', 'property_type',
            'preferred_date', 'preferred_date_display', 'preferred_time',
            'estimated_price', 'regular_price', 'discount_amount',
            'notes', 'page_url', 'source',
            'status', 'is_read',
            'remark', 'latest_remark', 'remark_count',
            'needs_comment_update', 'comment_status',
            'received_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'source',
            'remark', 'latest_remark', 'remark_count',
            'needs_comment_update', 'comment_status',
            'preferred_date_display', 'received_display',
            'created_at', 'updated_at',
        ]

    def get_comment_status(self, obj) -> str:
        needs = getattr(obj, 'needs_comment_update', None)
        if needs is None:
            latest = _resolve_latest_remark(obj)
            needs = latest is None
        return 'required' if needs else 'added'

    def get_remark(self, obj):
        latest = _resolve_latest_remark(obj)
        return latest.remark if latest else None

    def get_latest_remark(self, obj):
        return _serialize_latest_remark(_resolve_latest_remark(obj))

    def get_preferred_date_display(self, obj) -> str:
        if not obj.preferred_date:
            return ''
        return obj.preferred_date.strftime('%d/%m/%Y')

    def get_received_display(self, obj) -> str:
        if not obj.created_at:
            return ''
        return obj.created_at.strftime('%d/%m/%Y %I:%M %p')


def _money(value) -> float:
    return float(Decimal(value or 0))


def website_rate_payload(rate: DeepCleaningRate) -> dict:
    return {
        'id': rate.code,
        'segment': rate.segment,
        'service': rate.service,
        'package': rate.package_name,
        'unit': rate.billing_unit,
        'quantity': _money(rate.example_qty),
        'rate': _money(rate.rate_per_unit),
        'minimum': _money(rate.min_charge),
        'base': _money(rate.job_amount),
        'team': rate.technicians,
        'hours': rate.on_site_hours,
        'note': rate.scope_note,
    }


def website_amc_payload(rate: DeepCleaningRate) -> dict | None:
    if not rate.amc_visits:
        return None
    return {
        'id': rate.code,
        'segment': rate.segment,
        'package': f'{rate.service}: {rate.package_name}',
        'visits': rate.amc_visits,
        'perVisit': _money(rate.amc_per_visit),
        'annual': _money(rate.amc_annual),
        'interval': rate.amc_interval,
    }


def website_catalog(rates) -> dict:
    services = []
    for rate in rates:
        if rate.service not in services:
            services.append(rate.service)
    return {
        'discount': 0.3,
        'services': services,
        'rates': [website_rate_payload(rate) for rate in rates],
        'amc': [item for item in (website_amc_payload(rate) for rate in rates) if item],
    }


class DeepCleaningRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeepCleaningRate
        fields = [
            'id',
            'code',
            'segment',
            'service',
            'package_name',
            'billing_unit',
            'example_qty',
            'rate_per_unit',
            'min_charge',
            'job_amount',
            'technicians',
            'on_site_hours',
            'scope_note',
            'amc_visits',
            'amc_discount',
            'amc_per_visit',
            'amc_annual',
            'amc_interval',
            'is_active',
            'sort_order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_code(self, value: str) -> str:
        code = (value or '').strip().upper()
        if not code:
            raise serializers.ValidationError('Enter a rate code such as R1.')
        qs = DeepCleaningRate.objects.filter(code__iexact=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A rate with this code already exists.')
        return code

    def validate(self, attrs):
        job = attrs.get('job_amount', getattr(self.instance, 'job_amount', 0))
        minimum = attrs.get('min_charge', getattr(self.instance, 'min_charge', 0))
        if Decimal(job or 0) < 0 or Decimal(minimum or 0) < 0:
            raise serializers.ValidationError('Prices cannot be negative.')
        return attrs
