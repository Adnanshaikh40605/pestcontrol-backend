"""
Pest e-Card WhatsApp send check / mark APIs for DOH + Pest CRM.

GET  /api/e-card/sent-check/?mobile=9372792693
POST /api/e-card/mark-sent/
"""
from __future__ import annotations

from rest_framework import response, status, views
from rest_framework.throttling import UserRateThrottle

from .ecard_send import get_ecard_send_for_mobile, mark_ecard_sent, normalize_ecard_mobile
from .permissions import IsCRMOperationalUser


def _serialize_send(row) -> dict:
    return {
        'already_sent': True,
        'mobile': row.mobile,
        'template_name': row.template_name,
        'sent_at': row.sent_at.isoformat().replace('+00:00', 'Z') if row.sent_at else None,
        'sent_by': row.sent_by or '',
        'customer_name': row.customer_name or '',
        'source': row.source or '',
    }


class ECardSentCheckView(views.APIView):
    """
    Check if Pest e-Card WhatsApp was already sent to this mobile.
    Query: ?mobile=9372792693  (also accepts 91XXXXXXXXXX)
    """

    permission_classes = [IsCRMOperationalUser]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        raw = (
            request.query_params.get('mobile')
            or request.query_params.get('number')
            or request.query_params.get('phone')
            or ''
        )
        normalized = normalize_ecard_mobile(raw)
        if not normalized:
            return response.Response(
                {'error': 'Enter a valid 10-digit mobile number.', 'code': 'invalid_mobile'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        row = get_ecard_send_for_mobile(normalized)
        if not row:
            return response.Response({'already_sent': False, 'mobile': normalized})
        return response.Response(_serialize_send(row))


class ECardMarkSentView(views.APIView):
    """
    Record that Pest e-Card WhatsApp was sent to this mobile.
    Call AFTER WhatsFlow send succeeds.
    """

    permission_classes = [IsCRMOperationalUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        raw = data.get('mobile') or data.get('number') or data.get('phone') or ''
        normalized = normalize_ecard_mobile(raw)
        if not normalized:
            return response.Response(
                {'error': 'Enter a valid 10-digit mobile number.', 'code': 'invalid_mobile'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            row, created = mark_ecard_sent(
                mobile=normalized,
                user=request.user,
                sent_by=str(data.get('sent_by') or '').strip(),
                customer_name=str(data.get('customer_name') or data.get('name') or '').strip(),
                source=str(data.get('source') or '').strip(),
                template_name=str(data.get('template_name') or 'pestecardaadsd').strip(),
            )
        except ValueError as exc:
            return response.Response(
                {'error': str(exc), 'code': 'invalid_mobile'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = _serialize_send(row)
        payload['created'] = created
        return response.Response(
            payload,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
