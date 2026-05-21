"""Nested remark list/create and remark detail update/delete."""

from django.db.models import Count
from rest_framework import response, status, views
from rest_framework.pagination import PageNumberPagination

from .models import CRMInquiry, Inquiry, InquiryRemark, WebsiteLeadRemark, RemarkType, ActivityLog
from .permissions import IsCRMOperationalUser, IsRemarkAdmin
from .remark_serializers import InquiryRemarkSerializer, WebsiteLeadRemarkSerializer


class RemarkHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20


def _staff_display_name(user) -> str:
    if not user or not getattr(user, 'is_authenticated', False):
        return 'System'
    return user.get_full_name() or user.username


def _log_remark_activity(user, action: str, *, inquiry_label: str, old_text: str | None = None, new_text: str | None = None):
    parts = [inquiry_label]
    if old_text is not None and new_text is not None:
        parts.append(f"Updated:\n{old_text}\n→\n{new_text}")
    elif new_text:
        parts.append(new_text[:500])
    if user and getattr(user, 'is_authenticated', False):
        try:
            ActivityLog.objects.create(user=user, action=action, details='\n'.join(parts))
        except Exception:
            pass


class CRMInquiryRemarkListCreateView(views.APIView):
    permission_classes = [IsCRMOperationalUser]

    def get(self, request, inquiry_id):
        try:
            inquiry = CRMInquiry.objects.get(pk=inquiry_id)
        except CRMInquiry.DoesNotExist:
            return response.Response({'error': 'Inquiry not found'}, status=status.HTTP_404_NOT_FOUND)

        qs = InquiryRemark.objects.filter(inquiry=inquiry).select_related('created_by').order_by('-created_at')
        paginator = RemarkHistoryPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = InquiryRemarkSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, inquiry_id):
        try:
            inquiry = CRMInquiry.objects.get(pk=inquiry_id)
        except CRMInquiry.DoesNotExist:
            return response.Response({'error': 'Inquiry not found'}, status=status.HTTP_404_NOT_FOUND)

        text = (request.data.get('remark') or '').strip()
        if not text:
            return response.Response({'error': 'Remark text is required'}, status=status.HTTP_400_BAD_REQUEST)

        remark_type = request.data.get('remark_type') or RemarkType.NOTE
        if remark_type not in RemarkType.values:
            remark_type = RemarkType.NOTE

        entry = InquiryRemark.objects.create(
            inquiry=inquiry,
            remark=text,
            created_by=request.user,
            remark_type=remark_type,
        )
        _log_remark_activity(
            request.user,
            'Added CRM Inquiry Remark',
            inquiry_label=f"CRM Inquiry #{inquiry.id} ({inquiry.name})",
            new_text=text,
        )
        serializer = InquiryRemarkSerializer(entry, context={'request': request})
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


class CRMInquiryRemarkDetailView(views.APIView):
    permission_classes = [IsRemarkAdmin]

    def patch(self, request, pk):
        try:
            entry = InquiryRemark.objects.select_related('inquiry').get(pk=pk)
        except InquiryRemark.DoesNotExist:
            return response.Response({'error': 'Remark not found'}, status=status.HTTP_404_NOT_FOUND)

        new_text = (request.data.get('remark') or '').strip()
        if not new_text:
            return response.Response({'error': 'Remark text is required'}, status=status.HTTP_400_BAD_REQUEST)

        old_text = entry.remark
        entry.remark = new_text
        if 'remark_type' in request.data:
            rt = request.data.get('remark_type')
            if rt in RemarkType.values:
                entry.remark_type = rt
        entry.save(update_fields=['remark', 'remark_type', 'updated_at'])

        _log_remark_activity(
            request.user,
            'Updated CRM Inquiry Remark',
            inquiry_label=f"CRM Inquiry #{entry.inquiry_id}",
            old_text=old_text,
            new_text=new_text,
        )
        return response.Response(
            InquiryRemarkSerializer(entry, context={'request': request}).data
        )

    def delete(self, request, pk):
        try:
            entry = InquiryRemark.objects.select_related('inquiry').get(pk=pk)
        except InquiryRemark.DoesNotExist:
            return response.Response({'error': 'Remark not found'}, status=status.HTTP_404_NOT_FOUND)

        old_text = entry.remark
        inquiry_label = f"CRM Inquiry #{entry.inquiry_id}"
        entry.delete()
        _log_remark_activity(
            request.user,
            'Deleted CRM Inquiry Remark',
            inquiry_label=inquiry_label,
            old_text=old_text,
            new_text='(removed)',
        )
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class WebsiteLeadRemarkListCreateView(views.APIView):
    permission_classes = [IsCRMOperationalUser]

    def get(self, request, lead_id):
        try:
            lead = Inquiry.objects.get(pk=lead_id)
        except Inquiry.DoesNotExist:
            return response.Response({'error': 'Lead not found'}, status=status.HTTP_404_NOT_FOUND)

        qs = WebsiteLeadRemark.objects.filter(lead=lead).select_related('created_by').order_by('-created_at')
        paginator = RemarkHistoryPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = WebsiteLeadRemarkSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, lead_id):
        try:
            lead = Inquiry.objects.get(pk=lead_id)
        except Inquiry.DoesNotExist:
            return response.Response({'error': 'Lead not found'}, status=status.HTTP_404_NOT_FOUND)

        text = (request.data.get('remark') or '').strip()
        if not text:
            return response.Response({'error': 'Remark text is required'}, status=status.HTTP_400_BAD_REQUEST)

        remark_type = request.data.get('remark_type') or RemarkType.NOTE
        if remark_type not in RemarkType.values:
            remark_type = RemarkType.NOTE

        entry = WebsiteLeadRemark.objects.create(
            lead=lead,
            remark=text,
            created_by=request.user,
            remark_type=remark_type,
        )
        _log_remark_activity(
            request.user,
            'Added Website Lead Remark',
            inquiry_label=f"Website Lead #{lead.id} ({lead.name})",
            new_text=text,
        )
        serializer = WebsiteLeadRemarkSerializer(entry, context={'request': request})
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


class WebsiteLeadRemarkDetailView(views.APIView):
    permission_classes = [IsRemarkAdmin]

    def patch(self, request, pk):
        try:
            entry = WebsiteLeadRemark.objects.select_related('lead').get(pk=pk)
        except WebsiteLeadRemark.DoesNotExist:
            return response.Response({'error': 'Remark not found'}, status=status.HTTP_404_NOT_FOUND)

        new_text = (request.data.get('remark') or '').strip()
        if not new_text:
            return response.Response({'error': 'Remark text is required'}, status=status.HTTP_400_BAD_REQUEST)

        old_text = entry.remark
        entry.remark = new_text
        if 'remark_type' in request.data:
            rt = request.data.get('remark_type')
            if rt in RemarkType.values:
                entry.remark_type = rt
        entry.save(update_fields=['remark', 'remark_type', 'updated_at'])

        _log_remark_activity(
            request.user,
            'Updated Website Lead Remark',
            inquiry_label=f"Website Lead #{entry.lead_id}",
            old_text=old_text,
            new_text=new_text,
        )
        return response.Response(
            WebsiteLeadRemarkSerializer(entry, context={'request': request}).data
        )

    def delete(self, request, pk):
        try:
            entry = WebsiteLeadRemark.objects.select_related('lead').get(pk=pk)
        except WebsiteLeadRemark.DoesNotExist:
            return response.Response({'error': 'Remark not found'}, status=status.HTTP_404_NOT_FOUND)

        old_text = entry.remark
        inquiry_label = f"Website Lead #{entry.lead_id}"
        entry.delete()
        _log_remark_activity(
            request.user,
            'Deleted Website Lead Remark',
            inquiry_label=inquiry_label,
            old_text=old_text,
            new_text='(removed)',
        )
        return response.Response(status=status.HTTP_204_NO_CONTENT)


def annotate_remark_summary(queryset, remark_model, fk_field: str):
    """Annotate remark_count for list endpoints."""
    return queryset.annotate(remark_count=Count('remarks', distinct=True))
