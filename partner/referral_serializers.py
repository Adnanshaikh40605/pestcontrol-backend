from rest_framework import serializers

from .models import PartnerReferral
from .referral_utils import (
    PARTNER_STATUS_LABELS,
    partner_status_from_crm,
)


class PartnerReferralPartnerSerializer(serializers.ModelSerializer):
    """Partner app — list/detail referrals."""

    status = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    referred_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = PartnerReferral
        fields = [
            'id',
            'client_name',
            'mobile',
            'area',
            'status',
            'status_label',
            'referred_at',
            'updated_at',
        ]

    def _crm_status(self, obj):
        if obj.crm_inquiry_id:
            return obj.crm_inquiry.status
        return 'New'

    def get_status(self, obj):
        return partner_status_from_crm(self._crm_status(obj))

    def get_status_label(self, obj):
        return PARTNER_STATUS_LABELS.get(self.get_status(obj), 'Pending')


class PartnerReferralCrmSerializer(serializers.ModelSerializer):
    """CRM staff — partner referrals with technician metadata."""

    partner_id = serializers.IntegerField(source='partner.id', read_only=True)
    partner_name = serializers.CharField(source='partner.full_name', read_only=True)
    partner_mobile = serializers.CharField(source='partner.mobile', read_only=True)
    partner_role = serializers.CharField(source='partner.role', read_only=True)
    crm_inquiry_id = serializers.IntegerField(source='crm_inquiry.id', read_only=True, allow_null=True)
    crm_status = serializers.SerializerMethodField()
    partner_status = serializers.SerializerMethodField()
    partner_status_label = serializers.SerializerMethodField()
    referred_at = serializers.DateTimeField(source='created_at', read_only=True)
    inquiry_date = serializers.SerializerMethodField()
    inquiry_time = serializers.SerializerMethodField()

    class Meta:
        model = PartnerReferral
        fields = [
            'id',
            'client_name',
            'mobile',
            'area',
            'partner_id',
            'partner_name',
            'partner_mobile',
            'partner_role',
            'crm_inquiry_id',
            'crm_status',
            'partner_status',
            'partner_status_label',
            'referred_at',
            'inquiry_date',
            'inquiry_time',
            'created_at',
            'updated_at',
        ]

    def _crm_status(self, obj):
        if obj.crm_inquiry_id:
            return obj.crm_inquiry.status
        return 'New'

    def get_crm_status(self, obj):
        return self._crm_status(obj)

    def get_partner_status(self, obj):
        return partner_status_from_crm(self._crm_status(obj))

    def get_partner_status_label(self, obj):
        from .referral_utils import PARTNER_STATUS_LABELS

        return PARTNER_STATUS_LABELS.get(self.get_partner_status(obj), 'Pending')

    def get_inquiry_date(self, obj):
        if obj.crm_inquiry_id and obj.crm_inquiry.inquiry_date:
            return obj.crm_inquiry.inquiry_date.isoformat()
        return None

    def get_inquiry_time(self, obj):
        if obj.crm_inquiry_id and obj.crm_inquiry.inquiry_time:
            return obj.crm_inquiry.inquiry_time.isoformat()
        return None


class PartnerReferralStatusUpdateSerializer(serializers.Serializer):
    """CRM PATCH — update linked inquiry status."""

    status = serializers.ChoiceField(
        choices=['New', 'Contacted', 'Converted', 'Closed'],
    )
