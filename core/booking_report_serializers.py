from rest_framework import serializers

from .models import BookingReportClient, BookingReportClientRemark
from .remark_serializers import LatestRemarkSummarySerializer, _user_display


class BookingReportClientRemarkSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingReportClientRemark
        fields = [
            'id',
            'client',
            'remark',
            'remark_type',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'client',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]

    def get_created_by_name(self, obj):
        return _user_display(obj.created_by)


class BookingReportClientSerializer(serializers.ModelSerializer):
    remarks_count = serializers.IntegerField(read_only=True, default=0)
    latest_remark = serializers.SerializerMethodField()

    class Meta:
        model = BookingReportClient
        fields = [
            'id',
            'name',
            'mobile',
            'city',
            'remarks_count',
            'latest_remark',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_latest_remark(self, obj):
        # Prefetched in list/retrieve views when available
        remarks = getattr(obj, '_prefetched_objects_cache', {}).get('remarks')
        if remarks is not None:
            latest = remarks[0] if remarks else None
        else:
            latest = obj.remarks.select_related('created_by').order_by('-created_at').first()

        if not latest:
            return None
        return LatestRemarkSummarySerializer(
            {
                'id': latest.id,
                'remark': latest.remark,
                'remark_type': latest.remark_type,
                'created_by_name': _user_display(latest.created_by),
                'created_at': latest.created_at,
            }
        ).data
