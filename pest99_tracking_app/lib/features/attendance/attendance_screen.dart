import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/operations_provider.dart';
import '../../shared/widgets/empty_state.dart';

class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>(() => context.read<OperationsProvider>().loadAttendance());
  }

  String _time(dynamic v) {
    if (v == null) return '—';
    try {
      return DateFormat('HH:mm').format(DateTime.parse(v.toString()).toLocal());
    } catch (_) {
      return '—';
    }
  }

  String _formatDate(String? raw) {
    if (raw == null) return '';
    try {
      return DateFormat('d MMM').format(DateTime.parse(raw));
    } catch (_) {
      return raw;
    }
  }

  @override
  Widget build(BuildContext context) {
    final ops = context.watch<OperationsProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Attendance')),
      body: RefreshIndicator(
        onRefresh: ops.loadAttendance,
        color: AppColors.primary,
        child: ops.attendance.isEmpty
            ? ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  SizedBox(height: 60),
                  EmptyState(message: 'No attendance records yet', icon: Icons.event_note_outlined),
                ],
              )
            : ListView.separated(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(AppSpacing.screenEdge),
                itemCount: ops.attendance.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, i) {
                  final row = ops.attendance[i];
                  final isLate = row['is_late'] == true;
                  final hasRecord = row['check_in_at'] != null;
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.cardPadding),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(_formatDate(row['date']?.toString()), style: Theme.of(context).textTheme.titleMedium),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: (hasRecord ? AppColors.successText : AppColors.offDuty).withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: Text(
                                  hasRecord ? 'Present' : 'No record',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: hasRecord ? AppColors.successText : AppColors.offDuty,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          if (hasRecord) ...[
                            const SizedBox(height: 10),
                            Text(
                              'In ${_time(row['check_in_at'])}  ·  Out ${_time(row['check_out_at'])}',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                Text(
                                  '${row['total_distance_km'] ?? 0} km',
                                  style: Theme.of(context).textTheme.labelSmall,
                                ),
                                const Spacer(),
                                Text(
                                  isLate ? 'Late' : 'On time',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: isLate ? AppColors.warning : AppColors.successText,
                                  ),
                                ),
                              ],
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
