import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/operations_provider.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/section_header.dart';

class VisitsScreen extends StatefulWidget {
  const VisitsScreen({super.key});

  @override
  State<VisitsScreen> createState() => _VisitsScreenState();
}

class _VisitsScreenState extends State<VisitsScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>(() => context.read<OperationsProvider>().loadVisits());
  }

  @override
  Widget build(BuildContext context) {
    final ops = context.watch<OperationsProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text("Today's Visits")),
      body: RefreshIndicator(
        onRefresh: ops.loadVisits,
        color: AppColors.primary,
        child: ops.loading && ops.visits.isEmpty
            ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
            : ops.visits.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: const [
                      SizedBox(height: 60),
                      EmptyState(message: 'No visits scheduled for today', icon: Icons.place_outlined),
                    ],
                  )
                : ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(AppSpacing.screenEdge),
                    itemCount: ops.visits.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 12),
                    itemBuilder: (context, i) {
                      final v = ops.visits[i];
                      final status = v['status']?.toString() ?? 'scheduled';
                      final canAction = status == 'scheduled' || status == 'in_progress';
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.all(AppSpacing.cardPadding),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Text(
                                      v['title']?.toString() ?? 'Visit',
                                      style: Theme.of(context).textTheme.titleMedium,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  VisitStatusChip(status: status),
                                ],
                              ),
                              if (v['client_name'] != null && v['client_name'].toString().isNotEmpty) ...[
                                const SizedBox(height: 8),
                                Row(
                                  children: [
                                    const Icon(Icons.person_outline, size: 16, color: AppColors.textSecondary),
                                    const SizedBox(width: 6),
                                    Expanded(child: Text(v['client_name'].toString())),
                                  ],
                                ),
                              ],
                              if (v['address'] != null && v['address'].toString().isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Icon(Icons.location_on_outlined, size: 16, color: AppColors.textSecondary),
                                    const SizedBox(width: 6),
                                    Expanded(
                                      child: Text(
                                        v['address'].toString(),
                                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                              if (canAction) ...[
                                const SizedBox(height: 16),
                                SizedBox(
                                  width: double.infinity,
                                  child: FilledButton(
                                    onPressed: () async {
                                      final id = v['id'] as int;
                                      if (status == 'scheduled') {
                                        await ops.checkInVisit(id);
                                      } else {
                                        await ops.checkOutVisit(id);
                                      }
                                    },
                                    child: Text(status == 'scheduled' ? 'Check in' : 'Check out'),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}
