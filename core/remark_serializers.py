"""Serializers for inquiry remark history."""

from rest_framework import serializers

from .models import InquiryRemark, WebsiteLeadRemark


def _user_display(user) -> str:
    if not user:
        return 'System'
    return user.get_full_name() or user.username


class InquiryRemarkSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InquiryRemark
        fields = [
            'id', 'inquiry', 'remark', 'remark_type',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'inquiry', 'created_by', 'created_by_name', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return _user_display(obj.created_by)


class WebsiteLeadRemarkSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = WebsiteLeadRemark
        fields = [
            'id', 'lead', 'remark', 'remark_type',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'lead', 'created_by', 'created_by_name', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return _user_display(obj.created_by)


class LatestRemarkSummarySerializer(serializers.Serializer):
    """Compact latest remark for list rows."""
    id = serializers.IntegerField(allow_null=True)
    remark = serializers.CharField(allow_blank=True)
    remark_type = serializers.CharField(allow_blank=True)
    created_by_name = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField(allow_null=True)
