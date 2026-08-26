import 'dart:typed_data';

import 'package:intl/intl.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../config/legal_config.dart';

/// Builds a branded Pest Control 99 tax-style invoice PDF from API payload.
Future<Uint8List> buildCustomerInvoicePdf(Map<String, dynamic> inv) async {
  final doc = pw.Document();
  final code = '${inv['code'] ?? inv['booking_id'] ?? ''}';
  final amount = _money(inv['amount']);
  final payment = _paymentLabel(inv['payment_status']?.toString());
  final schedule = _formatDate(inv['schedule_datetime']?.toString());
  final issued = _formatDate(inv['issued_at']?.toString());
  final addressParts = [
    '${inv['address'] ?? ''}'.trim(),
    '${inv['area'] ?? ''}'.trim(),
    '${inv['city'] ?? ''}'.trim(),
  ].where((e) => e.isNotEmpty).join(', ');
  final property = [
    '${inv['property_type'] ?? ''}'.trim(),
    '${inv['bhk_size'] ?? ''}'.trim(),
  ].where((e) => e.isNotEmpty).join(' · ');

  doc.addPage(
    pw.Page(
      pageFormat: PdfPageFormat.a4,
      margin: const pw.EdgeInsets.all(36),
      build: (context) {
        return pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            pw.Row(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Expanded(
                  child: pw.Column(
                    crossAxisAlignment: pw.CrossAxisAlignment.start,
                    children: [
                      pw.Text(
                        LegalConfig.brandName.toUpperCase(),
                        style: pw.TextStyle(
                          fontSize: 20,
                          fontWeight: pw.FontWeight.bold,
                          color: PdfColor.fromInt(0xFF0A4F16),
                        ),
                      ),
                      pw.SizedBox(height: 4),
                      pw.Text(
                        'A Brand of ${LegalConfig.companyLegalName}',
                        style: const pw.TextStyle(fontSize: 10, color: PdfColors.grey700),
                      ),
                      pw.SizedBox(height: 6),
                      pw.Text(LegalConfig.supportPhone, style: const pw.TextStyle(fontSize: 10)),
                      pw.Text(LegalConfig.supportEmail, style: const pw.TextStyle(fontSize: 10)),
                      pw.Text(LegalConfig.websiteBase, style: const pw.TextStyle(fontSize: 10)),
                    ],
                  ),
                ),
                pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.end,
                  children: [
                    pw.Text(
                      'INVOICE',
                      style: pw.TextStyle(fontSize: 22, fontWeight: pw.FontWeight.bold),
                    ),
                    pw.SizedBox(height: 6),
                    pw.Text('Invoice No. $code', style: const pw.TextStyle(fontSize: 11)),
                    pw.Text('Issued: $issued', style: const pw.TextStyle(fontSize: 10)),
                    pw.SizedBox(height: 6),
                    pw.Container(
                      padding: const pw.EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: pw.BoxDecoration(
                        color: payment.toLowerCase().contains('paid') &&
                                !payment.toLowerCase().contains('after')
                            ? PdfColor.fromInt(0xFFE8F5E9)
                            : PdfColor.fromInt(0xFFFFF3E0),
                        borderRadius: pw.BorderRadius.circular(4),
                      ),
                      child: pw.Text(
                        payment,
                        style: pw.TextStyle(fontSize: 10, fontWeight: pw.FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            pw.SizedBox(height: 20),
            pw.Divider(color: PdfColors.grey400),
            pw.SizedBox(height: 14),
            pw.Text('Bill To', style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold)),
            pw.SizedBox(height: 4),
            pw.Text('${inv['client_name'] ?? 'Customer'}', style: const pw.TextStyle(fontSize: 12)),
            if ('${inv['mobile'] ?? ''}'.trim().isNotEmpty)
              pw.Text('+91 ${inv['mobile']}', style: const pw.TextStyle(fontSize: 10)),
            if (addressParts.isNotEmpty)
              pw.Text(addressParts, style: const pw.TextStyle(fontSize: 10)),
            if (property.isNotEmpty)
              pw.Text(property, style: const pw.TextStyle(fontSize: 10, color: PdfColors.grey700)),
            pw.SizedBox(height: 18),
            pw.Table(
              border: pw.TableBorder.all(color: PdfColors.grey400, width: 0.6),
              columnWidths: {
                0: const pw.FlexColumnWidth(3.2),
                1: const pw.FlexColumnWidth(1.2),
                2: const pw.FlexColumnWidth(1.2),
              },
              children: [
                pw.TableRow(
                  decoration: const pw.BoxDecoration(color: PdfColor.fromInt(0xFFE8F5E9)),
                  children: [
                    _th('Description'),
                    _th('Schedule'),
                    _th('Amount (₹)', align: pw.TextAlign.right),
                  ],
                ),
                pw.TableRow(
                  children: [
                    _td(
                      '${inv['service_type'] ?? 'Pest Control Service'}'
                      '${'${inv['time_slot'] ?? ''}'.trim().isEmpty ? '' : '\nTime slot: ${inv['time_slot']}'}',
                    ),
                    _td(schedule),
                    _td(amount, align: pw.TextAlign.right),
                  ],
                ),
              ],
            ),
            pw.SizedBox(height: 14),
            pw.Align(
              alignment: pw.Alignment.centerRight,
              child: pw.Container(
                width: 220,
                padding: const pw.EdgeInsets.all(10),
                decoration: pw.BoxDecoration(
                  border: pw.Border.all(color: PdfColors.grey400),
                  borderRadius: pw.BorderRadius.circular(6),
                ),
                child: pw.Row(
                  mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                  children: [
                    pw.Text('Total Payable', style: pw.TextStyle(fontWeight: pw.FontWeight.bold, fontSize: 12)),
                    pw.Text('₹$amount', style: pw.TextStyle(fontWeight: pw.FontWeight.bold, fontSize: 13)),
                  ],
                ),
              ),
            ),
            pw.SizedBox(height: 18),
            pw.Text(
              'Payment note: Online payment in app is currently disabled. '
              'Please pay after service completion as confirmed with our team.',
              style: const pw.TextStyle(fontSize: 9, color: PdfColors.grey700),
            ),
            pw.Spacer(),
            pw.Divider(color: PdfColors.grey400),
            pw.SizedBox(height: 8),
            pw.Text(
              'Thank you for choosing ${LegalConfig.brandName}.',
              style: pw.TextStyle(fontSize: 10, fontWeight: pw.FontWeight.bold),
            ),
            pw.Text(
              'This is a computer-generated invoice.',
              style: const pw.TextStyle(fontSize: 8, color: PdfColors.grey600),
            ),
          ],
        );
      },
    ),
  );

  return doc.save();
}

pw.Widget _th(String text, {pw.TextAlign align = pw.TextAlign.left}) {
  return pw.Padding(
    padding: const pw.EdgeInsets.all(8),
    child: pw.Text(
      text,
      textAlign: align,
      style: pw.TextStyle(fontSize: 10, fontWeight: pw.FontWeight.bold),
    ),
  );
}

pw.Widget _td(String text, {pw.TextAlign align = pw.TextAlign.left}) {
  return pw.Padding(
    padding: const pw.EdgeInsets.all(8),
    child: pw.Text(text, textAlign: align, style: const pw.TextStyle(fontSize: 10)),
  );
}

String _money(dynamic raw) {
  final n = double.tryParse('$raw'.replaceAll(',', ''));
  if (n == null) return '$raw';
  return NumberFormat('#,##0.00', 'en_IN').format(n);
}

String _formatDate(String? raw) {
  if (raw == null || raw.isEmpty) return '—';
  try {
    return DateFormat('d MMM yyyy').format(DateTime.parse(raw).toLocal());
  } catch (_) {
    return raw;
  }
}

String _paymentLabel(String? raw) {
  final s = (raw ?? '').toLowerCase();
  if (s.contains('paid') && !s.contains('unpaid')) return 'Paid';
  if (s.contains('partial')) return 'Partially paid';
  return 'Pay after service';
}
