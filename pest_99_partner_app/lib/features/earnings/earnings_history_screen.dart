import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/user_error.dart';
import '../../models/partner_earnings.dart';
import '../../services/earnings_service.dart';
import '../../shared/widgets/async_error_view.dart';

class EarningsHistoryScreen extends StatefulWidget {
  const EarningsHistoryScreen({super.key});

  @override
  State<EarningsHistoryScreen> createState() => _EarningsHistoryScreenState();
}

class _EarningsHistoryScreenState extends State<EarningsHistoryScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  EarningsHistory? _earnings;
  List<PartnerSettlement> _settlements = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final svc = EarningsService(context.read<ApiClient>());
      final earnings = await svc.getEarnings();
      final settlements = await svc.getSettlements();
      if (!mounted) return;
      setState(() {
        _earnings = earnings;
        _settlements = settlements;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = userErrorMessage(e, fallback: 'Could not load earnings.');
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Earnings'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        bottom: TabBar(
          controller: _tabs,
          tabs: const [
            Tab(text: 'History'),
            Tab(text: 'Settlements'),
          ],
        ),
      ),
      body: _loading && _earnings == null
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _earnings == null
              ? AsyncErrorView(message: _error!, onRetry: _load)
              : TabBarView(
                  controller: _tabs,
                  children: [
                    _EarningsTab(history: _earnings!, onRefresh: _load),
                    _SettlementsTab(items: _settlements, onRefresh: _load),
                  ],
                ),
    );
  }
}

class _EarningsTab extends StatelessWidget {
  const _EarningsTab({required this.history, required this.onRefresh});

  final EarningsHistory history;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('dd MMM yyyy');
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.screenEdge),
        children: [
          Row(
            children: [
              Expanded(
                child: _SummaryCard(
                  label: 'Total',
                  value: '₹${history.totalEarnings}',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _SummaryCard(
                  label: 'Approved',
                  value: '₹${history.approvedEarnings}',
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          if (history.results.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 48),
              child: Column(
                children: [
                  Icon(Icons.payments_outlined, size: 56, color: AppColors.textSecondary),
                  const SizedBox(height: 12),
                  Text(
                    'No earnings yet',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                  ),
                ],
              ),
            )
          else
            ...history.results.map((e) {
              DateTime? when;
              if (e.completedAt != null) {
                when = DateTime.tryParse(e.completedAt!);
              }
              return Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  title: Text(e.jobCode?.isNotEmpty == true ? e.jobCode! : 'Job earning'),
                  subtitle: Text(
                    [
                      if (e.serviceType != null && e.serviceType!.isNotEmpty) e.serviceType!,
                      if (when != null) dateFmt.format(when.toLocal()),
                      if (e.settlementStatus != null) 'Settlement: ${e.settlementStatus}',
                      if (e.payoutStatus != null) 'Payout: ${e.payoutStatus}',
                    ].join(' · '),
                  ),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '₹${e.amount}',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      Text(
                        e.isApproved ? 'Approved' : 'Pending',
                        style: TextStyle(
                          fontSize: 12,
                          color: e.isApproved ? AppColors.successText : AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }
}

class _SettlementsTab extends StatelessWidget {
  const _SettlementsTab({required this.items, required this.onRefresh});

  final List<PartnerSettlement> items;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: items.isEmpty
          ? ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                const SizedBox(height: 64),
                Icon(Icons.receipt_long_outlined, size: 56, color: AppColors.textSecondary),
                const SizedBox(height: 12),
                Text(
                  'No settlements yet',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
              ],
            )
          : ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(AppSpacing.screenEdge),
              itemCount: items.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final s = items[i];
                return Card(
                  child: ListTile(
                    title: Text('${s.periodStart} → ${s.periodEnd}'),
                    subtitle: Text('${s.cadence} · ${s.status}'),
                    trailing: Text(
                      '₹${s.netAmount}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ),
                );
              },
            ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: AppColors.textSecondary,
              )),
          const SizedBox(height: 6),
          Text(value, style: Theme.of(context).textTheme.headlineSmall),
        ],
      ),
    );
  }
}
