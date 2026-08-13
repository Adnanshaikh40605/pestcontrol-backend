import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/operations_provider.dart';
import '../../shared/widgets/empty_state.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>(() => context.read<OperationsProvider>().loadTasks());
  }

  Color _statusColor(String status) {
    if (status == 'completed' || status == 'verified') return AppColors.successText;
    if (status == 'in_progress') return AppColors.infoBlue;
    return AppColors.warning;
  }

  @override
  Widget build(BuildContext context) {
    final ops = context.watch<OperationsProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('My Tasks')),
      body: RefreshIndicator(
        onRefresh: ops.loadTasks,
        color: AppColors.primary,
        child: ops.tasks.isEmpty
            ? ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: [
                  if (ops.loading) const LinearProgressIndicator(color: AppColors.primary),
                  const SizedBox(height: 60),
                  const EmptyState(message: 'No tasks assigned', icon: Icons.task_alt_outlined),
                ],
              )
            : ListView.separated(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(AppSpacing.screenEdge),
                itemCount: ops.tasks.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (context, i) {
                  final t = ops.tasks[i];
                  final status = t['status']?.toString() ?? 'pending';
                  final done = status == 'completed' || status == 'verified';
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.cardPadding),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(t['title']?.toString() ?? 'Task', style: Theme.of(context).textTheme.titleMedium),
                                if (t['description'] != null && t['description'].toString().isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Text(
                                    t['description'].toString(),
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
                                  ),
                                ],
                                const SizedBox(height: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: _statusColor(status).withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    status.replaceAll('_', ' '),
                                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: _statusColor(status)),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          done
                              ? const Icon(Icons.check_circle, color: AppColors.successText, size: 32)
                              : FilledButton(
                                  onPressed: () => ops.completeTask(t['id'] as int),
                                  style: FilledButton.styleFrom(minimumSize: const Size(72, 40), padding: const EdgeInsets.symmetric(horizontal: 12)),
                                  child: const Text('Done'),
                                ),
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
