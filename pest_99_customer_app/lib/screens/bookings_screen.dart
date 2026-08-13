import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_spacing.dart';
import '../models/customer_models.dart';
import '../services/customer_services.dart';
import '../shared/widgets/pc99_widgets.dart';
import '../shared/widgets/section_card.dart';

class BookingsScreen extends StatefulWidget {
  const BookingsScreen({super.key, this.historyOnly = false});

  final bool historyOnly;

  @override
  State<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends State<BookingsScreen> {
  List<CustomerBooking> _items = [];
  List<AmcScheduleGroup> _amcGroups = [];
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
      final list = widget.historyOnly ? await svc.history() : await svc.list();
      List<AmcScheduleGroup> amc = const [];
      if (widget.historyOnly) {
        try {
          amc = await svc.amcSchedule();
        } catch (_) {
          amc = const [];
        }
      }
      if (!mounted) return;
      setState(() {
        _items = list;
        _amcGroups = amc;
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
    if (raw == null || raw.isEmpty) return 'Unscheduled';
    try {
      return DateFormat('d MMM yyyy, h:mm a').format(DateTime.parse(raw).toLocal());
    } catch (_) {
      return raw;
    }
  }

  StatusTone _statusTone(String? status) {
    final s = (status ?? '').toLowerCase();
    if (s == 'done' || s == 'completed') return StatusTone.success;
    if (s.contains('cancel')) return StatusTone.danger;
    if (s.contains('pending') || s.contains('upcoming')) return StatusTone.warning;
    if (s.contains('process') || s.contains('accepted')) return StatusTone.info;
    return StatusTone.neutral;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: Text(widget.historyOnly ? 'Service history' : 'My bookings'),
        centerTitle: true,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.screenEdge),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!, textAlign: TextAlign.center),
                        TextButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : _items.isEmpty && _amcGroups.isEmpty
                  ? Pc99EmptyBookPrompt(
                      title: widget.historyOnly ? 'No completed services yet' : 'No bookings yet',
                      subtitle: 'You haven’t booked any service yet. Tap Book to schedule pest control for your property.',
                      onBook: () => context.push('/book/property'),
                    )
                  : RefreshIndicator(
                      color: AppColors.primary,
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.all(AppSpacing.screenEdge),
                        children: [
                          if (widget.historyOnly && _amcGroups.isNotEmpty) ...[
                            Text('AMC schedule', style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 12),
                            ..._amcGroups.map((g) {
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: SectionCard(
                                  child: Theme(
                                    data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                                    child: ExpansionTile(
                                      tilePadding: EdgeInsets.zero,
                                      childrenPadding: EdgeInsets.zero,
                                      title: Text(
                                        g.parent.serviceType,
                                        style: Theme.of(context).textTheme.headlineSmall,
                                      ),
                                      subtitle: Text(
                                        g.parent.code ?? '#${g.parent.id}',
                                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                              color: AppColors.textSecondary,
                                            ),
                                      ),
                                      children: [
                                        if (g.visits.isEmpty)
                                          const Padding(
                                            padding: EdgeInsets.only(bottom: 8),
                                            child: Text('No follow-up visits yet'),
                                          )
                                        else
                                          ...g.visits.map(
                                            (v) => ListTile(
                                              contentPadding: EdgeInsets.zero,
                                              title: Text(v.serviceType),
                                              subtitle: Text(
                                                '${v.status ?? ''} · ${_formatDate(v.scheduleDatetime)}',
                                              ),
                                              trailing: Text('₹${v.invoiceAmount ?? v.price ?? '—'}'),
                                              onTap: () => context.push('/booking/${v.id}'),
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            }),
                            const SizedBox(height: 8),
                            Text('Completed services', style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 12),
                          ],
                          if (_items.isEmpty)
                            Pc99EmptyBookPrompt(
                              title: 'No bookings yet',
                              subtitle: 'Book a service to see it listed here.',
                              onBook: () => context.push('/book/property'),
                            )
                          else
                            ..._items.map(
                              (b) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: SectionCard(
                                  onTap: () => context.push('/booking/${b.id}'),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(
                                            child: Text(
                                              b.serviceType,
                                              style: Theme.of(context).textTheme.headlineSmall,
                                            ),
                                          ),
                                          StatusChip(
                                            label: b.status ?? 'Pending',
                                            tone: _statusTone(b.status),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        b.code ?? '#${b.id}',
                                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                              color: AppColors.textSecondary,
                                            ),
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        _formatDate(b.scheduleDatetime),
                                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                              color: AppColors.textSecondary,
                                            ),
                                      ),
                                      if (b.clientAddress != null && b.clientAddress!.isNotEmpty) ...[
                                        const SizedBox(height: 4),
                                        Text(
                                          b.clientAddress!,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                                color: AppColors.textSecondary,
                                              ),
                                        ),
                                      ],
                                      const SizedBox(height: 12),
                                      Row(
                                        children: [
                                          StatusChip(
                                            label: b.paymentStatus ?? 'Unpaid',
                                            tone: b.isPaid ? StatusTone.success : StatusTone.warning,
                                          ),
                                          const Spacer(),
                                          Text(
                                            '₹${b.invoiceAmount ?? b.price ?? '—'}',
                                            style: Theme.of(context).textTheme.titleMedium,
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
    );
  }
}
