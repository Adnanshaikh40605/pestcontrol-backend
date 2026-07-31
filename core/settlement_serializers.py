"""Serializers for technician settlements."""
from rest_framework import serializers

from core.models import SettlementLineItem, TechnicianSettlement


class SettlementLineItemSerializer(serializers.ModelSerializer):
    job_code = serializers.CharField(source='job.code', read_only=True)
    technician_name = serializers.CharField(
        source='participation.technician.name',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = SettlementLineItem
        fields = [
            'id', 'settlement', 'job', 'job_code', 'participation', 'technician_name',
            'partner_earning', 'earning_type', 'amount', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class TechnicianSettlementSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source='technician.name', read_only=True)
    technician_mobile = serializers.CharField(source='technician.mobile', read_only=True)
    partner_name = serializers.CharField(source='partner.full_name', read_only=True, allow_null=True)
    approved_by_name = serializers.SerializerMethodField()
    paid_by_name = serializers.SerializerMethodField()
    line_items = SettlementLineItemSerializer(many=True, read_only=True)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianSettlement
        fields = [
            'id', 'technician', 'technician_name', 'technician_mobile',
            'partner', 'partner_name',
            'period_start', 'period_end', 'cadence', 'status',
            'gross_amount', 'incentive_amount', 'deduction_amount', 'net_amount',
            'notes', 'approved_at', 'approved_by', 'approved_by_name',
            'paid_at', 'paid_by', 'paid_by_name',
            'line_count', 'line_items',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'gross_amount', 'incentive_amount', 'deduction_amount', 'net_amount',
            'approved_at', 'approved_by', 'paid_at', 'paid_by',
            'line_count', 'line_items', 'created_at', 'updated_at',
        ]

    def get_line_count(self, obj):
        return obj.line_items.count()

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None

    def get_paid_by_name(self, obj):
        if obj.paid_by:
            return obj.paid_by.get_full_name() or obj.paid_by.username
        return None


class SettlementBuildSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    cadence = serializers.ChoiceField(
        choices=TechnicianSettlement.Cadence.choices,
        default=TechnicianSettlement.Cadence.WEEKLY,
    )
    technician_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
