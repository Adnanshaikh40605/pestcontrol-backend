import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:printing/printing.dart';
import 'package:provider/provider.dart';

import '../config/legal_config.dart';
import '../core/api_client.dart';
import '../core/theme/app_colors.dart';
import '../services/customer_services.dart';
import '../services/invoice_pdf.dart';
import '../shared/widgets/pc99_widgets.dart';

/// Proper invoice preview + Download / Print PDF.
class InvoiceScreen extends StatefulWidget {
  const InvoiceScreen({super.key, required this.bookingId});

  final int bookingId;

  @override
  State<InvoiceScreen> createState() => _InvoiceScreenState();
}

class _InvoiceScreenState extends State<InvoiceScreen> {
  Map<String, dynamic>? _inv;
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final inv = await BookingService(context.read<ApiClient>()).invoice(widget.bookingId);
      if (!mounted) return;
      setState(() {
        _inv = inv;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  String _money(dynamic raw) {
    final n = double.tryParse('$raw'.replaceAll(',', ''));
    if (n == null) return '₹${raw ?? '—'}';
    return '₹${NumberFormat('#,##0.00', 'en_IN').format(n)}';
  }

  String _date(dynamic raw) {
    final s = '$raw';
    if (s.isEmpty || s == 'null') return '—';
    try {
      return DateFormat('EEE, d MMM yyyy').format(DateTime.parse(s).toLocal());
    } catch (_) {
      return s;
    }
  }

  String _paymentLabel(dynamic raw) {
    final s = '$raw'.toLowerCase();
    if (s.contains('paid') && !s.contains('unpaid')) return 'Paid';
    if (s.contains('partial')) return 'Partially paid';
    return 'Pay after service';
  }

  Future<void> _download() async {
    final inv = _inv;
    if (inv == null) return;
    setState(() => _busy = true);
    try {
      final bytes = await buildCustomerInvoicePdf(inv);
      final code = '${inv['code'] ?? widget.bookingId}';
      await Printing.sharePdf(bytes: bytes, filename: 'PC99-Invoice-$code.pdf');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not create invoice PDF: $e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _print() async {
    final inv = _inv;
    if (inv == null) return;
    setState(() => _busy = true);
    try {
      final bytes = await buildCustomerInvoicePdf(inv);
      await Printing.layoutPdf(onLayout: (_) async => bytes);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open print dialog: $e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final inv = _inv;
    final paidLabel = inv == null ? '' : _paymentLabel(inv['payment_status']);
    final isPaid = paidLabel == 'Paid';

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Invoice'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => context.pop(),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!, textAlign: TextAlign.center),
                      TextButton(onPressed: _load, child: const Text('Retry')),
                    ],
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
                  children: [
                    Pc99Card(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Expanded(child: Pc99Logo(height: 36)),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  const Text('INVOICE', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                                  const SizedBox(height: 4),
                                  Text(
                                    'No. ${inv!['code'] ?? widget.bookingId}',
                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                                  ),
                                  Text(
                                    'Issued ${_date(inv['issued_at'])}',
                                    style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'A Brand of ${LegalConfig.companyLegalName}',
                            style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                          ),
                          Text(LegalConfig.supportPhone, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          Text(LegalConfig.supportEmail, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          const SizedBox(height: 14),
                          const Divider(height: 1, color: AppColors.divider),
                          const SizedBox(height: 12),
                          const Text('Bill To', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppColors.textMuted)),
                          const SizedBox(height: 4),
                          Text(
                            '${inv['client_name'] ?? 'Customer'}',
                            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                          ),
                          if ('${inv['mobile'] ?? ''}'.trim().isNotEmpty)
                            Text('+91 ${inv['mobile']}', style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                          if ('${inv['address'] ?? ''}${inv['city'] ?? ''}'.trim().isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(
                              [
                                '${inv['address'] ?? ''}'.trim(),
                                '${inv['area'] ?? ''}'.trim(),
                                '${inv['city'] ?? ''}'.trim(),
                              ].where((e) => e.isNotEmpty).join(', '),
                              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, height: 1.3),
                            ),
                          ],
                          const SizedBox(height: 14),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppColors.successBg,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppColors.border),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${inv['service_type'] ?? 'Pest Control Service'}',
                                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                                ),
                                const SizedBox(height: 6),
                                Text('Schedule: ${_date(inv['schedule_datetime'])}', style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                                if ('${inv['time_slot'] ?? ''}'.trim().isNotEmpty)
                                  Text('Time slot: ${inv['time_slot']}', style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                                const SizedBox(height: 10),
                                Row(
                                  children: [
                                    const Text('Amount', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                                    const Spacer(),
                                    Text(
                                      _money(inv['amount']),
                                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: AppColors.primary),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              const Text('Payment status', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: isPaid ? AppColors.successBg : const Color(0xFFFFF7ED),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  paidLabel,
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w800,
                                    color: isPaid ? AppColors.primary : AppColors.warning,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          const Text(
                            'Pay after service completion. Online payment in the app is currently off.',
                            style: TextStyle(fontSize: 11, color: AppColors.textMuted, height: 1.35),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      height: 48,
                      child: ElevatedButton.icon(
                        onPressed: _busy ? null : _download,
                        icon: _busy
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.download_rounded),
                        label: const Text('Download Invoice PDF', style: TextStyle(fontWeight: FontWeight.w800)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 44,
                      child: OutlinedButton.icon(
                        onPressed: _busy ? null : _print,
                        icon: const Icon(Icons.print_outlined, size: 18),
                        label: const Text('Print Invoice', style: TextStyle(fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.primary,
                          side: const BorderSide(color: AppColors.primary),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }
}
