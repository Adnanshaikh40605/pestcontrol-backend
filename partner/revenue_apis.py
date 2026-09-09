"""
Partner app revenue-model APIs: presence, leave requests, settlements (read-only).
"""
from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from core.models import Technician, TechnicianSettlement
from partner.models import PartnerLeaveRequest
from partner.permissions import IsPartner
from partner.presence import presence_payload
from partner.serializers import (
    PartnerLeaveRequestSerializer,
    PartnerSettlementSerializer,
)
from partner.services import PartnerBookingError
from partner.views_base import PartnerAPIView


class PresenceAPIView(PartnerAPIView):
    """
    GET  /api/partner/presence/  — the technician's work status
    POST /api/partner/presence/  — rejected; the CRM desk owns this status

    The status is Active / On Leave / Suspended, all three of which are
    business decisions the office makes. The route stays mounted so an older
    app build gets a readable message instead of a 404, and so leave keeps
    going through the leave-request flow below rather than a self-toggle.
    """

    permission_classes = [IsPartner]

    @extend_schema(tags=['Presence'], summary='Get work status')
    def get(self, request):
        return Response(presence_payload(request.partner))

    @extend_schema(tags=['Presence'], summary='Not settable from the app')
    def post(self, request):
        return Response(
            {
                'error': (
                    'Your work status is set by the office. To take leave, '
                    'raise a leave request.'
                ),
                'code': 'presence_read_only',
                'presence': presence_payload(request.partner),
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class LeaveRequestListCreateAPIView(PartnerAPIView):
    """
    GET  /api/partner/leave-requests/
    POST /api/partner/leave-requests/
    """

    permission_classes = [IsPartner]

    @extend_schema(tags=['Leave'], summary='List my leave requests')
    def get(self, request):
        qs = PartnerLeaveRequest.objects.filter(partner=request.partner).order_by('-created_at')
        return Response({'results': PartnerLeaveRequestSerializer(qs, many=True).data})

    @extend_schema(tags=['Leave'], summary='Submit a leave request')
    def post(self, request):
        serializer = PartnerLeaveRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        leave = serializer.save(partner=request.partner)
        return Response(
            PartnerLeaveRequestSerializer(leave).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveRequestCancelAPIView(PartnerAPIView):
    """POST /api/partner/leave-requests/{id}/cancel/"""

    permission_classes = [IsPartner]

    @extend_schema(tags=['Leave'], summary='Cancel a pending leave request')
    def post(self, request, id):
        try:
            leave = PartnerLeaveRequest.objects.get(id=id, partner=request.partner)
        except PartnerLeaveRequest.DoesNotExist:
            return Response({'error': 'Leave request not found.'}, status=404)
        if leave.status != PartnerLeaveRequest.Status.PENDING:
            return Response(
                {
                    'error': 'Only pending leave requests can be cancelled.',
                    'code': 'invalid_state',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        leave.status = PartnerLeaveRequest.Status.CANCELLED
        leave.save(update_fields=['status', 'updated_at'])
        return Response(PartnerLeaveRequestSerializer(leave).data)


class PartnerSettlementsAPIView(PartnerAPIView):
    """
    GET /api/partner/settlements/
    Read-only list of approved/paid settlements for this partner.
    """

    permission_classes = [IsPartner]

    @extend_schema(tags=['Settlements'], summary='List my settlements (read-only)')
    def get(self, request):
        partner = request.partner
        tech = getattr(partner, 'core_technician', None)
        q = Q(partner=partner)
        if tech is not None:
            q |= Q(technician=tech)
        qs = (
            TechnicianSettlement.objects.filter(q)
            .filter(
                status__in=[
                    TechnicianSettlement.Status.APPROVED,
                    TechnicianSettlement.Status.PAID,
                ]
            )
            .distinct()
            .order_by('-period_end')
        )
        return Response({'results': PartnerSettlementSerializer(qs, many=True).data})
