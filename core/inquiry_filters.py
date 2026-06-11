"""Shared list filtering helpers for CRM inquiries and website leads."""
from __future__ import annotations

from django.db.models import Count, Q, QuerySet
from django.utils.dateparse import parse_date


INQUIRY_STATUSES = ('New', 'Contacted', 'Converted', 'Closed')


def parse_request_date(value: str | None):
    if not value or not str(value).strip():
        return None
    return parse_date(str(value).strip())


def apply_inquiry_search(qs: QuerySet, request, *, fields: tuple[str, ...]) -> QuerySet:
    """Apply q/search text filter across configured icontains fields."""
    q = request.query_params.get('q', request.query_params.get('search', '')).strip()
    if not q:
        return qs

    q_filters = Q()
    for field in fields:
        q_filters |= Q(**{f'{field}__icontains': q})
    if q.isdigit():
        q_filters |= Q(pk=int(q))
    return qs.filter(q_filters)


def apply_date_range_filter(
    qs: QuerySet,
    request,
    *,
    date_field: str = 'created_at',
) -> QuerySet:
    """
    Filter by from/to (inclusive) query params.

    CRM inquiries use inquiry_date (DateField).
    Website leads use created_at (DateTimeField, filtered by date part).
    Legacy single-day inquiry_date=YYYY-MM-DD is still supported for CRM.
    """
    from_date = parse_request_date(request.query_params.get('from'))
    to_date = parse_request_date(request.query_params.get('to'))
    single_date = parse_request_date(request.query_params.get('inquiry_date'))

    if date_field == 'inquiry_date':
        if from_date:
            qs = qs.filter(inquiry_date__gte=from_date)
        if to_date:
            qs = qs.filter(inquiry_date__lte=to_date)
        if not from_date and not to_date and single_date:
            qs = qs.filter(inquiry_date=single_date)
        return qs

    if from_date:
        qs = qs.filter(created_at__date__gte=from_date)
    if to_date:
        qs = qs.filter(created_at__date__lte=to_date)
    return qs


def get_status_counts(qs: QuerySet) -> dict[str, int]:
    """Return status breakdown for tab badges (all filters except status)."""
    rows = qs.values('status').annotate(count=Count('id', distinct=True))
    by_status = {row['status']: row['count'] for row in rows}
    total = sum(by_status.values())
    return {
        'all': total,
        'New': by_status.get('New', 0),
        'Contacted': by_status.get('Contacted', 0),
        'Converted': by_status.get('Converted', 0),
        'Closed': by_status.get('Closed', 0),
    }


class InquiryListCountsMixin:
    """
    Mixin for inquiry list endpoints: date/search filters + status_counts in response.
    Subclasses set date_filter_field and search_fields_list.
    """
    date_filter_field: str = 'created_at'
    search_fields_list: tuple[str, ...] = ('name', 'mobile', 'email')
    extra_list_filters = None  # optional callable(qs, request) -> qs

    def _base_list_queryset(self, *, include_status: bool = True) -> QuerySet:
        qs = super().get_queryset()

        focus = self.request.query_params.get('focus')
        if focus and str(focus).isdigit():
            return qs.filter(pk=int(focus))

        qs = apply_inquiry_search(qs, self.request, fields=self.search_fields_list)
        qs = apply_date_range_filter(qs, self.request, date_field=self.date_filter_field)

        if self.extra_list_filters:
            qs = self.extra_list_filters(qs, self.request)

        if include_status:
            status = self.request.query_params.get('status', '').strip()
            if status:
                qs = qs.filter(status=status)

        return qs

    def get_queryset(self):
        return self._base_list_queryset(include_status=True)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        counts_qs = self._base_list_queryset(include_status=False)
        status_counts = get_status_counts(counts_qs)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['status_counts'] = status_counts
            return response

        serializer = self.get_serializer(queryset, many=True)
        return response.Response({
            'count': queryset.count(),
            'results': serializer.data,
            'status_counts': status_counts,
        })
