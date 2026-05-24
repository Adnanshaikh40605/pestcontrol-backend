import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from core.views import BaseModelViewSet

from .models import PartnerReferral
from .referral_serializers import (
    PartnerReferralCrmSerializer,
    PartnerReferralStatusUpdateSerializer,
)

logger = logging.getLogger(__name__)


class PartnerReferralViewSet(BaseModelViewSet):
    """
    CRM API for partner-submitted client referrals.
    PATCH status updates the linked CRM inquiry (single source of truth).
    """

    queryset = PartnerReferral.objects.select_related('partner', 'crm_inquiry')
    serializer_class = PartnerReferralCrmSerializer
    http_method_names = ['get', 'head', 'options', 'patch']
    search_fields = [
        'client_name',
        'mobile',
        'area',
        'partner__full_name',
        'partner__mobile',
    ]
    filterset_fields = ['partner']
    ordering_fields = ['created_at', 'client_name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(crm_inquiry__status=status_param)
        partner_status = self.request.query_params.get('partner_status')
        if partner_status:
            from .referral_utils import crm_status_from_partner

            crm_val = crm_status_from_partner(partner_status)
            qs = qs.filter(crm_inquiry__status=crm_val)
        q = self.request.query_params.get('q', self.request.query_params.get('search', ''))
        if q:
            filters_q = (
                Q(client_name__icontains=q)
                | Q(mobile__icontains=q)
                | Q(area__icontains=q)
                | Q(partner__full_name__icontains=q)
                | Q(partner__mobile__icontains=q)
            )
            if str(q).isdigit():
                filters_q |= Q(pk=int(q))
            qs = qs.filter(filters_q)
        return qs

    def partial_update(self, request, *args, **kwargs):
        referral = self.get_object()
        ser = PartnerReferralStatusUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        new_status = ser.validated_data['status']
        if not referral.crm_inquiry_id:
            return Response(
                {'error': 'No linked CRM inquiry for this referral.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        inquiry = referral.crm_inquiry
        inquiry.status = new_status
        inquiry.save(update_fields=['status', 'updated_at'])
        referral.save(update_fields=['updated_at'])
        logger.info(
            'CRM user %s set partner referral %s status to %s',
            request.user,
            referral.id,
            new_status,
        )
        return Response(PartnerReferralCrmSerializer(referral).data)
