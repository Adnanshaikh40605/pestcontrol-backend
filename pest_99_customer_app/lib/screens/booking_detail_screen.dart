import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_spacing.dart';
import '../models/customer_models.dart';
import '../services/customer_services.dart';
import '../shared/widgets/section_card.dart';

class BookingDetailScreen extends StatefulWidget {
  const BookingDetailScreen({super.key, required this.bookingId});

  final int bookingId;

  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen> {
  CustomerBooking? _booking;
  Map<String, dynamic>? _invoice;
  bool _loading = true;
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
      final svc = BookingService(context.read<ApiClient>());
      final booking = await svc.detail(widget.bookingId);
      Map<String, dynamic>? invoice;
      try {
        invoice = await svc.invoice(widget.bookingId);
      } catch (_) {
        invoice = null;
      }
      if (!mounted) return;
      setState(() {
        _booking = booking;
        _invoice = invoice;
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

  String _formatDate(String? raw) {
    if (raw == null || raw.isEmpty) return 'To be confirmed';
    try {
      return DateFormat('EEE, d MMM yyyy · h:mm a').format(DateTime.parse(raw).toLocal());
    } catch (_) {
      return raw;
    }
  }

  Future<void> _rate() async {
    final rating = await showDialog<int>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Rate your service'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (var i = 5; i >= 1; i--)
              ListTile(
                leading: Icon(Icons.star, color: AppColors.warning),
                title: Text('$i star${i == 1 ? '' : 's'}'),
                onTap: () => Navigator.pop(ctx, i),
              ),
          ],
        ),
      ),
    );
    if (rating == null || !mounted) return;
    try {
      await BookingService(context.read<ApiClient>()).rate(widget.bookingId, rating: rating);
      if (!mounted) return;
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Thanks for your feedback!')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e'), backgroundColor: AppColors.danger),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final b = _booking;
    return Scaffold(
      appBar: AppBar(title: Text(b?.code ?? 'Booking')),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!),
                      TextButton(onPressed: _load, child: const Text('Retry')),
                    ],
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(AppSpacing.screenEdge),
                  children: [
                    SectionCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            b!.serviceType,
                            style: Theme.of(context).textTheme.headlineMedium,
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              StatusChip(label: b.status ?? 'Pending', tone: StatusTone.info),
                              StatusChip(
                                label: b.paymentStatus ?? 'Unpaid',
                                tone: b.isPaid ? StatusTone.success : StatusTone.warning,
                              ),
                              if (b.packageTier != null && b.packageTier!.isNotEmpty)
                                StatusChip(
                                  label: b.packageTier!,
                                  tone: StatusTone.neutral,
                                ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          _DetailRow(label: 'Schedule', value: _formatDate(b.scheduleDatetime)),
                          if (b.timeSlot != null && b.timeSlot!.isNotEmpty)
                            _DetailRow(label: 'Time slot', value: b.timeSlot!),
                          _DetailRow(
                            label: 'Amount',
                            value: '₹${b.invoiceAmount ?? b.price ?? '—'}',
                          ),
                          if (b.clientAddress != null && b.clientAddress!.isNotEmpty)
                            _DetailRow(label: 'Address', value: b.clientAddress!),
                          if (b.city != null && b.city!.isNotEmpty)
                            _DetailRow(label: 'City', value: b.city!),
                          if (b.propertyType != null && b.propertyType!.isNotEmpty)
                            _DetailRow(
                              label: 'Property',
                              value: [
                                b.propertyType!,
                                if (b.bhkSize != null && b.bhkSize!.isNotEmpty) b.bhkSize!,
                              ].join(' · '),
                            ),
                          if (b.bookingType != null && b.bookingType!.isNotEmpty)
                            _DetailRow(label: 'Type', value: b.bookingType!),
                          if (b.notes != null && b.notes!.isNotEmpty)
                            _DetailRow(label: 'Notes', value: b.notes!),
                        ],
                      ),
                    ),
                    if (_invoice != null) ...[
                      const SizedBox(height: 16),
                      SectionCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Invoice', style: Theme.of(context).textTheme.headlineSmall),
                            const SizedBox(height: 12),
                            _DetailRow(label: 'Code', value: '${_invoice!['code'] ?? '—'}'),
                            _DetailRow(label: 'Amount', value: '₹${_invoice!['amount'] ?? '—'}'),
                            _DetailRow(
                              label: 'Payment',
                              value: '${_invoice!['payment_status'] ?? '—'}',
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                    if (!b.isPaid)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppColors.successSoft,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                        ),
                        child: const Text(
                          'Pay after service. Online payment will be enabled once the payment gateway is live.',
                          style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                        ),
                      ),
                    if (b.canRate) ...[
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: _rate,
                        icon: const Icon(Icons.star_outline),
                        label: const Text('Rate & review'),
                      ),
                    ],
                    if (b.myRating != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        'Your rating: ${b.myRating!['rating']} ★',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                    ],
                    const SizedBox(height: 16),
                    Text(
                      'Our team will confirm your booking shortly.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                    ),
                  ],
                ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 96,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyLarge),
          ),
        ],
      ),
    );
  }
}
