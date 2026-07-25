"""
E-Card tracking APIs.

POST /api/e-card/track/     — public, lightweight visit log (AllowAny)
GET  /api/e-card/tracking/  — CRM list + summary (JWT)
"""
from __future__ import annotations

import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework import response, status, views
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .ecard_tracking import (
    detect_device_type,
    detect_traffic_source,
    get_client_ip,
    resolve_city,
)
from .models import ECardVisit
from .permissions import IsCRMOperationalUser

logger = logging.getLogger(__name__)


class ECardTrackThrottle(AnonRateThrottle):
    """Limit abuse on the public track endpoint."""

    rate = '60/min'


class ECardTrackingPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        # `data` is a dict: {results, total_visitors, today_visitors, count}
        if isinstance(data, dict) and 'results' in data:
            return response.Response(
                {
                    'count': data.get('count', self.page.paginator.count),
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                    'total_visitors': data.get('total_visitors', 0),
                    'today_visitors': data.get('today_visitors', 0),
                    'results': data.get('results', []),
                }
            )
        return super().get_paginated_response(data)


def _serialize_visit(visit: ECardVisit) -> dict:
    local = timezone.localtime(visit.visited_at)
    return {
        'city': visit.city or 'Unknown',
        'device_type': visit.device_type,
        'traffic_source': visit.traffic_source,
        'visited_at': local.strftime('%Y-%m-%d %H:%M:%S'),
    }


class ECardTrackView(views.APIView):
    """
    POST /api/e-card/track/

    Body (all optional — server derives the rest):
      referrer, landing_url, utm_source, user_agent, city
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ECardTrackThrottle]

    def post(self, request):
        data = request.data if hasattr(request, 'data') else {}
        user_agent = (
            str(data.get('user_agent') or request.META.get('HTTP_USER_AGENT') or '')
        )[:512]
        referrer = str(data.get('referrer') or request.META.get('HTTP_REFERER') or '')[:500]
        landing_url = str(data.get('landing_url') or '')[:500]
        utm_source = str(data.get('utm_source') or '')[:100]
        client_city = str(data.get('city') or '')[:100]

        device_type = detect_device_type(user_agent)
        traffic_source = detect_traffic_source(referrer, utm_source, landing_url)
        city = resolve_city(request, client_city)
        ip = get_client_ip(request)

        visit = ECardVisit.objects.create(
            city=city or 'Unknown',
            device_type=device_type,
            traffic_source=traffic_source,
            visited_at=timezone.now(),
            ip_address=ip,
            user_agent=user_agent,
            referrer=referrer,
        )
        return response.Response(
            _serialize_visit(visit),
            status=status.HTTP_201_CREATED,
        )


class ECardTrackingListView(views.APIView):
    """
    GET /api/e-card/tracking/

    Query: page, page_size, city, device_type, traffic_source, date_from, date_to, search
    """

    permission_classes = [IsCRMOperationalUser]
    throttle_classes = [UserRateThrottle]
    pagination_class = ECardTrackingPagination

    def get(self, request):
        qs = ECardVisit.objects.all()

        city = (request.query_params.get('city') or '').strip()
        if city:
            qs = qs.filter(city__icontains=city)

        device_type = (request.query_params.get('device_type') or '').strip()
        if device_type:
            qs = qs.filter(device_type__iexact=device_type)

        traffic_source = (request.query_params.get('traffic_source') or '').strip()
        if traffic_source:
            qs = qs.filter(traffic_source__iexact=traffic_source)

        date_from = (
            request.query_params.get('date_from')
            or request.query_params.get('from')
            or ''
        ).strip()
        date_to = (
            request.query_params.get('date_to')
            or request.query_params.get('to')
            or ''
        ).strip()
        if date_from:
            qs = qs.filter(visited_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(visited_at__date__lte=date_to)

        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        if search:
            qs = qs.filter(
                Q(city__icontains=search)
                | Q(traffic_source__icontains=search)
                | Q(device_type__icontains=search)
            )

        qs = qs.order_by('-visited_at', '-id')

        today = timezone.localdate()
        total_visitors = ECardVisit.objects.count()
        today_visitors = ECardVisit.objects.filter(visited_at__date=today).count()
        filtered_count = qs.count()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        results = [_serialize_visit(v) for v in (page or [])]

        return paginator.get_paginated_response(
            {
                'count': filtered_count,
                'total_visitors': total_visitors,
                'today_visitors': today_visitors,
                'results': results,
            }
        )
