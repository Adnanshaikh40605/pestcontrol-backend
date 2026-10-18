"""Serializers for DeepCleaning99 inquiries (isolated from pest Website Leads)."""

from __future__ import annotations

from rest_framework import serializers

from decimal import Decimal

from .models import (
    DeepCleaningBooking,
    DeepCleaningInquiry,
    DeepCleaningInquiryRemark,
    DeepCleaningRate,
    DeepCleaningTechnician,
)
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
    booking_id = serializers.SerializerMethodField()
    booking_code = serializers.SerializerMethodField()

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
            'booking_id', 'booking_code',
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
            'booking_id', 'booking_code',
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

    def _booking(self, obj):
        try:
            return obj.booking
        except DeepCleaningBooking.DoesNotExist:
            return None

    def get_booking_id(self, obj):
        booking = self._booking(obj)
        return booking.id if booking else None

    def get_booking_code(self, obj):
        booking = self._booking(obj)
        return booking.code if booking else ''


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


def _choice_list(values, allowed, label: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise serializers.ValidationError(f'Select at least one {label}.')
    cleaned = []
    for item in values:
        text = str(item or '').strip()
        if text not in allowed:
            raise serializers.ValidationError(f'{text or "Blank"} is not a valid {label}.')
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def _with_normalized_mobiles(data):
    incoming = data.copy() if hasattr(data, 'copy') else dict(data)
    from .deepcleaning_services import DeepCleaningInquiryService
    for field in ('mobile', 'alternative_mobile'):
        raw = incoming.get(field) if hasattr(incoming, 'get') else None
        if raw:
            incoming[field] = DeepCleaningInquiryService._normalize_mobile(raw)
    return incoming


class DeepCleaningTechnicianSerializer(serializers.ModelSerializer):
    presence_label = serializers.CharField(source='get_presence_status_display', read_only=True)
    is_available_for_work = serializers.BooleanField(read_only=True)

    class Meta:
        model = DeepCleaningTechnician
        fields = [
            'id', 'name', 'mobile', 'age', 'alternative_mobile',
            'address', 'location', 'cities', 'services',
            'presence_status', 'presence_label', 'is_active',
            'is_available_for_work',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'presence_label', 'is_available_for_work',
            'created_at', 'updated_at',
        ]

    def to_internal_value(self, data):
        return super().to_internal_value(_with_normalized_mobiles(data))

    def validate_name(self, value: str) -> str:
        text = (value or '').strip()
        if len(text) < 2:
            raise serializers.ValidationError('Enter the technician name.')
        return text

    def validate_mobile(self, value: str) -> str:
        mobile = DeepCleaningInquiryService_mobile(value)
        qs = DeepCleaningTechnician.objects.filter(mobile=mobile)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A technician with this mobile already exists.')
        return mobile

    def validate_alternative_mobile(self, value):
        if not value:
            return None
        return DeepCleaningInquiryService_mobile(value)

    def validate_cities(self, value):
        return _choice_list(value, DeepCleaningTechnician.CITIES, 'city')

    def validate_services(self, value):
        return _choice_list(value, DeepCleaningTechnician.SERVICES, 'service')

    def validate_age(self, value):
        if value in (None, ''):
            return None
        if value < 18 or value > 80:
            raise serializers.ValidationError('Age must be between 18 and 80.')
        return value

    def validate(self, attrs):
        mobile = attrs.get('mobile', getattr(self.instance, 'mobile', ''))
        alt = attrs.get('alternative_mobile', getattr(self.instance, 'alternative_mobile', None))
        if alt and alt == mobile:
            raise serializers.ValidationError({'alternative_mobile': 'Use a different alternate mobile.'})
        return attrs


def DeepCleaningInquiryService_mobile(raw) -> str:
    from .deepcleaning_services import DeepCleaningInquiryService
    mobile = DeepCleaningInquiryService._normalize_mobile(raw)
    if len(mobile) != 10 or mobile[0] not in '6789':
        raise serializers.ValidationError('Enter a 10-digit mobile number.')
    return mobile


class DeepCleaningBookingSerializer(serializers.ModelSerializer):
    technician_name = serializers.SerializerMethodField()
    technician_mobile = serializers.SerializerMethodField()
    preferred_date_display = serializers.SerializerMethodField()

    class Meta:
        model = DeepCleaningBooking
        fields = [
            'id', 'code', 'inquiry',
            'technician', 'technician_name', 'technician_mobile',
            'name', 'mobile', 'email', 'city', 'area', 'address',
            'segment', 'service', 'package_name', 'package_id',
            'quantity', 'unit', 'plan',
            'property_size', 'property_type',
            'preferred_date', 'preferred_date_display', 'preferred_time',
            'price', 'notes', 'status',
            'assigned_at', 'completed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'code', 'inquiry',
            'technician', 'technician_name', 'technician_mobile',
            'status', 'assigned_at', 'completed_at',
            'preferred_date_display',
            'created_at', 'updated_at',
        ]

    def to_internal_value(self, data):
        return super().to_internal_value(_with_normalized_mobiles(data))

    def get_technician_name(self, obj) -> str:
        return obj.technician.name if obj.technician_id else ''

    def get_technician_mobile(self, obj) -> str:
        return obj.technician.mobile if obj.technician_id else ''

    def get_preferred_date_display(self, obj) -> str:
        if not obj.preferred_date:
            return ''
        return obj.preferred_date.strftime('%d/%m/%Y')

    def validate_name(self, value: str) -> str:
        text = (value or '').strip()
        if len(text) < 2:
            raise serializers.ValidationError('Enter the customer name.')
        return text

    def validate_address(self, value: str) -> str:
        text = (value or '').strip()
        if len(text) < 5:
            raise serializers.ValidationError('Enter the area, building and full address.')
        return text

    def validate_mobile(self, value: str) -> str:
        return DeepCleaningInquiryService_mobile(value)

    def validate_service(self, value: str) -> str:
        service = (value or '').strip()
        if service not in DeepCleaningTechnician.SERVICES:
            raise serializers.ValidationError('Choose a Deep Cleaning service.')
        return service

    def validate_city(self, value: str) -> str:
        city = (value or '').strip()
        if city not in DeepCleaningTechnician.CITIES:
            raise serializers.ValidationError('Choose a service city.')
        return city

    def validate_price(self, value):
        if value in (None, ''):
            return None
        if Decimal(value) < 0:
            raise serializers.ValidationError('Price cannot be negative.')
        return value

    def validate(self, attrs):
        if self.instance and self.instance.status == DeepCleaningBooking.Status.DONE:
            raise serializers.ValidationError('A finished booking cannot be edited.')
        if self.instance and self.instance.status == DeepCleaningBooking.Status.CANCELLED:
            raise serializers.ValidationError('A cancelled booking cannot be edited.')
        if (
            self.instance
            and self.instance.status == DeepCleaningBooking.Status.ON_PROCESS
            and self.instance.technician_id
        ):
            service = attrs.get('service', self.instance.service)
            city = attrs.get('city', self.instance.city)
            technician = self.instance.technician
            if service not in (technician.services or []) or city not in (technician.cities or []):
                raise serializers.ValidationError(
                    'Remove the technician before changing to a service or city they do not cover.'
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            validated_data['created_by'] = user
        validated_data['status'] = DeepCleaningBooking.Status.PENDING
        return super().create(validated_data)
