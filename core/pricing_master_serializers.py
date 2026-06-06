from rest_framework import serializers

from .models import PricingRate, PricingRateAuditLog, PricingRegion


class PricingRegionSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = PricingRegion
        fields = [
            'id', 'slug', 'name', 'city', 'city_name', 'is_default', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PricingRateSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    region_slug = serializers.CharField(source='region.slug', read_only=True)
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PricingRate
        fields = [
            'id', 'region', 'region_name', 'region_slug',
            'service_package', 'plan_type', 'area_key', 'property_category',
            'amount', 'is_active', 'notes',
            'updated_by', 'updated_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'updated_by', 'updated_by_name']

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return None

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Amount cannot be negative.')
        return value


class PricingRateAuditLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PricingRateAuditLog
        fields = [
            'id', 'rate', 'region_slug', 'service_package', 'plan_type', 'area_key',
            'property_category', 'old_amount', 'new_amount', 'action',
            'changed_by', 'changed_by_name', 'change_note', 'created_at',
        ]
        read_only_fields = fields

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return None
