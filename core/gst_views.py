"""Purchase bills, CA email settings, and the monthly GST package."""

from datetime import date

from django.core.mail import EmailMessage
from django.http import HttpResponse
from rest_framework import serializers, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.gst_invoice import (
    build_monthly_package,
    build_monthly_workbook,
    invoice_pdf_lines,
    month_bounds,
    simple_pdf,
)
from core.models import CaReportDispatch, GstCaSettings, PurchaseBill
from core.payment_utils import quantize_money
from core.views import StandardListPagination


class PurchaseBillSerializer(serializers.ModelSerializer):
    attachment_name = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseBill
        fields = [
            'id', 'supplier_name', 'supplier_gstin', 'bill_number', 'bill_date',
            'taxable_amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount',
            'attachment', 'attachment_name', 'input_eligibility', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_amount', 'created_at', 'updated_at', 'attachment_name']

    def get_attachment_name(self, obj):
        if not obj.attachment:
            return ''
        return obj.attachment.name.rsplit('/', 1)[-1]

    def validate_supplier_gstin(self, value):
        cleaned = (value or '').strip().upper()
        if cleaned.startswith('GSTIN'):
            cleaned = cleaned[5:].strip()
        if len(cleaned) < 15:
            raise serializers.ValidationError('Supplier GSTIN is required on a purchase bill.')
        return cleaned

    def validate(self, attrs):
        taxable = quantize_money(attrs.get('taxable_amount', getattr(self.instance, 'taxable_amount', 0)))
        cgst = quantize_money(attrs.get('cgst_amount', getattr(self.instance, 'cgst_amount', 0)))
        sgst = quantize_money(attrs.get('sgst_amount', getattr(self.instance, 'sgst_amount', 0)))
        igst = quantize_money(attrs.get('igst_amount', getattr(self.instance, 'igst_amount', 0)))
        attrs['taxable_amount'] = taxable
        attrs['cgst_amount'] = cgst
        attrs['sgst_amount'] = sgst
        attrs['igst_amount'] = igst
        attrs['total_amount'] = quantize_money(taxable + cgst + sgst + igst)
        return attrs


class PurchaseBillViewSet(viewsets.ModelViewSet):
    queryset = PurchaseBill.objects.all()
    serializer_class = PurchaseBillSerializer
    pagination_class = StandardListPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['supplier_name', 'supplier_gstin', 'bill_number']
    ordering = ['-bill_date', '-id']


class GstCaSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GstCaSettings
        fields = ['ca_email', 'updated_at']


class GstCaSettingsView(APIView):
    def get(self, request):
        return Response(GstCaSettingsSerializer(GstCaSettings.load()).data)

    def patch(self, request):
        settings_row = GstCaSettings.load()
        serializer = GstCaSettingsSerializer(settings_row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


def _period_from_request(request):
    raw = (request.query_params.get('month') or request.data.get('month') or '').strip()
    today = date.today()
    if not raw:
        year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    else:
        year_text, month_text = raw.split('-', 1)
        year, month = int(year_text), int(month_text)
    if month < 1 or month > 12:
        raise ValueError('month')
    return year, month


class GstReportView(APIView):
    def get(self, request):
        try:
            year, month = _period_from_request(request)
        except (ValueError, AttributeError):
            return Response({'detail': 'Use month=YYYY-MM.'}, status=status.HTTP_400_BAD_REQUEST)
        kind = request.query_params.get('format', 'xlsx')
        if kind == 'zip':
            payload = build_monthly_package(year, month)
            response = HttpResponse(payload, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="gst-package-{year:04d}-{month:02d}.zip"'
            return response
        payload = build_monthly_workbook(year, month)
        response = HttpResponse(
            payload,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="gst-report-{year:04d}-{month:02d}.xlsx"'
        return response


class GstReportEmailView(APIView):
    def get(self, request):
        rows = CaReportDispatch.objects.all()[:20]
        return Response([
            {
                'period_start': row.period_start,
                'period_end': row.period_end,
                'ca_email': row.ca_email,
                'status': row.status,
                'detail': row.detail,
                'created_at': row.created_at,
            }
            for row in rows
        ])

    def post(self, request):
        try:
            year, month = _period_from_request(request)
        except (ValueError, AttributeError):
            return Response({'detail': 'Use month=YYYY-MM.'}, status=status.HTTP_400_BAD_REQUEST)
        start, end = month_bounds(year, month)
        settings_row = GstCaSettings.load()
        ca_email = (settings_row.ca_email or '').strip()
        if not ca_email:
            return Response({'detail': 'Save the CA email in settings first.'}, status=status.HTTP_400_BAD_REQUEST)
        package = build_monthly_package(year, month)
        status_label = 'sent'
        detail = ''
        try:
            message = EmailMessage(
                subject=f'Multi Pest Care LLP GST package {start.isoformat()} to {end.isoformat()}',
                body=(
                    'Monthly GST package: sales Excel, sales invoice PDFs, and purchase bill attachments. '
                    'Purchase GST is recorded for GSTR-2B matching. Only rows the CA marks eligible are deducted '
                    'from output GST in the Summary sheet.'
                ),
                to=[ca_email],
            )
            message.attach(f'gst-package-{year:04d}-{month:02d}.zip', package, 'application/zip')
            sent = message.send(fail_silently=False)
            if not sent:
                status_label = 'failed'
                detail = 'The mail server accepted no message.'
        except Exception as exc:
            status_label = 'failed'
            detail = str(exc)
        row = CaReportDispatch.objects.create(
            period_start=start,
            period_end=end,
            ca_email=ca_email,
            status=status_label,
            detail=detail,
        )
        http_status = status.HTTP_200_OK if status_label == 'sent' else status.HTTP_502_BAD_GATEWAY
        return Response(
            {'status': row.status, 'detail': row.detail, 'ca_email': ca_email},
            status=http_status,
        )


def email_invoice_to_customer(invoice):
    if not invoice.customer_email:
        return False, 'Add the customer email on the invoice first.'
    pdf = simple_pdf(invoice_pdf_lines(invoice))
    try:
        message = EmailMessage(
            subject=f'Tax invoice {invoice.invoice_no} — Multi Pest Care LLP',
            body=f'Please find tax invoice {invoice.invoice_no} attached.',
            to=[invoice.customer_email],
        )
        message.attach(f'{invoice.invoice_no}.pdf', pdf, 'application/pdf')
        message.send(fail_silently=False)
    except Exception as exc:
        return False, str(exc)
    return True, ''
