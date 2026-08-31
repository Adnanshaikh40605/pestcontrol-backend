import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

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
  bool _cancelling = false;
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

  Future<void> _callTechnician(String mobile) async {
    final cleaned = mobile.replaceAll(RegExp(r'[^\d+]'), '');
    if (cleaned.isEmpty) return;
    final uri = Uri.parse(cleaned.startsWith('+') ? 'tel:$cleaned' : 'tel:+91$cleaned');
    await launchUrl(uri);
  }

  Future<void> _cancelBooking() async {
    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel booking'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Please share a short reason for cancellation.',
              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 3,
              maxLength: 500,
              decoration: const InputDecoration(
                hintText: 'e.g. Plans changed, wrong date selected',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Keep booking')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Cancel booking', style: TextStyle(color: AppColors.danger)),
          ),
        ],
      ),
    );
    if (reason == null || !mounted) return;
    if (reason.trim().length < 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a reason (at least 4 characters).'),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }
    setState(() => _cancelling = true);
    try {
      final updated = await BookingService(context.read<ApiClient>()).cancel(
        widget.bookingId,
        reason: reason,
      );
      if (!mounted) return;
      setState(() {
        _booking = updated;
        _cancelling = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Booking cancelled.')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _cancelling = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e'), backgroundColor: AppColors.danger),
      );
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
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 18,
                                ),
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: [
                              StatusChip(
                                label: b.visitStatusLabel,
                                tone: b.isDone
                                    ? StatusTone.success
                                    : (b.isCancelled
                                        ? StatusTone.danger
                                        : StatusTone.info),
                              ),
                              StatusChip(
                                label: b.paymentStatusLabel,
                                tone: b.isPaid
                                    ? StatusTone.success
                                    : (b.priceConfirmationPending
                                        ? StatusTone.info
                                        : StatusTone.warning),
                              ),
                              if (b.planTypeLabel != null)
                                StatusChip(
                                  label: b.planTypeLabel!,
                                  tone: StatusTone.neutral,
                                ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          _DetailRow(label: 'Schedule', value: _formatDate(b.scheduleDatetime)),
                          if (b.timeSlot != null && b.timeSlot!.isNotEmpty)
                            _DetailRow(label: 'Preferred time', value: b.timeSlot!),
                          _DetailRow(
                            label: 'Total booking amount',
                            value: b.priceConfirmationPending
                                ? 'Pending confirmation'
                                : '₹${b.invoiceAmount ?? b.price ?? '—'}',
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
                          if (b.planTypeLabel != null)
                            _DetailRow(label: 'Plan', value: b.planTypeLabel!),
                          if (b.customerNotes != null)
                            _DetailRow(label: 'Notes', value: b.customerNotes!),
                        ],
                      ),
                    ),
                    if (b.hasAssignedTechnician) ...[
                      const SizedBox(height: 16),
                      SectionCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Assigned technician',
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                CircleAvatar(
                                  radius: 28,
                                  backgroundColor: AppColors.primary.withValues(alpha: 0.12),
                                  backgroundImage: (b.technicianPhotoUrl != null &&
                                          b.technicianPhotoUrl!.trim().isNotEmpty)
                                      ? NetworkImage(b.technicianPhotoUrl!)
                                      : null,
                                  child: (b.technicianPhotoUrl == null ||
                                          b.technicianPhotoUrl!.trim().isEmpty)
                                      ? Text(
                                          b.technicianName!.trim().isNotEmpty
                                              ? b.technicianName!.trim()[0].toUpperCase()
                                              : 'T',
                                          style: const TextStyle(
                                            color: AppColors.primary,
                                            fontWeight: FontWeight.w800,
                                            fontSize: 20,
                                          ),
                                        )
                                      : null,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        b.technicianName!,
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w800,
                                          fontSize: 15,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        b.visitStatusLabel,
                                        style: const TextStyle(
                                          color: AppColors.textSecondary,
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                if ((b.technicianMobile ?? '').trim().isNotEmpty)
                                  IconButton.filled(
                                    onPressed: () => _callTechnician(b.technicianMobile!),
                                    style: IconButton.styleFrom(
                                      backgroundColor: AppColors.primary,
                                      foregroundColor: Colors.white,
                                    ),
                                    icon: const Icon(Icons.call_rounded),
                                    tooltip: 'Call technician',
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
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
                              value: b.paymentStatusLabel,
                            ),
                            const SizedBox(height: 12),
                            SizedBox(
                              width: double.infinity,
                              height: 44,
                              child: ElevatedButton.icon(
                                onPressed: () => context.push('/invoice/${b.id}'),
                                icon: const Icon(Icons.download_rounded, size: 18),
                                label: const Text('View & Download Invoice', style: TextStyle(fontWeight: FontWeight.w800)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppColors.primary,
                                  foregroundColor: Colors.white,
                                  elevation: 0,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                    if (!b.isPaid && !b.isCancelled)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: b.priceConfirmationPending
                              ? const Color(0xFFFFF7ED)
                              : AppColors.successSoft,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: (b.priceConfirmationPending ? AppColors.warning : AppColors.primary)
                                .withValues(alpha: 0.3),
                          ),
                        ),
                        child: Text(
                          b.priceConfirmationPending
                              ? 'Price confirmation pending. Our team will confirm the final amount shortly.'
                              : 'Payment status: Unpaid. Pay after service once the amount is confirmed.',
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                        ),
                      ),
                    if (b.canCancel) ...[
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        height: 46,
                        child: OutlinedButton.icon(
                          onPressed: _cancelling ? null : _cancelBooking,
                          icon: _cancelling
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.cancel_outlined, color: AppColors.danger),
                          label: Text(
                            _cancelling ? 'Cancelling…' : 'Cancel Booking',
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              color: AppColors.danger,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: AppColors.danger),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                    ],
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
                    if (!b.hasAssignedTechnician && !b.isCancelled && !b.isDone) ...[
                      const SizedBox(height: 16),
                      Text(
                        'Our team will confirm your booking shortly. Technician details appear after assignment.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: AppColors.textSecondary,
                            ),
                      ),
                    ],
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
            width: 120,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
