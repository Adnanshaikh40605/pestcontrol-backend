"""Serializers for DeepCleaning99 inquiries (isolated from pest Website Leads)."""

from __future__ import annotations

from rest_framework import serializers

from .models import DeepCleaningInquiry, DeepCleaningInquiryRemark
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
