import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/operations_provider.dart';
import '../../shared/widgets/section_header.dart';

class LeaveScreen extends StatefulWidget {
  const LeaveScreen({super.key});

  @override
  State<LeaveScreen> createState() => _LeaveScreenState();
}

class _LeaveScreenState extends State<LeaveScreen> {
  int? _selectedTypeId;
  final _reason = TextEditingController();
  DateTime _start = DateTime.now();
  DateTime _end = DateTime.now();

  @override
  void initState() {
    super.initState();
    Future<void>(() => context.read<OperationsProvider>().loadLeave());
  }

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  String _fmt(DateTime d) => DateFormat('d MMM yyyy').format(d);

  Color _statusColor(String? status) {
    switch (status) {
      case 'approved':
        return AppColors.successText;
      case 'rejected':
        return AppColors.danger;
      default:
        return AppColors.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    final ops = context.watch<OperationsProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Leave')),
      body: RefreshIndicator(
        onRefresh: ops.loadLeave,
        color: AppColors.primary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.screenEdge),
          children: [
            const SectionHeader('Balance'),
            ...ops.leaveBalances.map(
              (b) => Card(
                child: ListTile(
                  title: Text(b['leave_type_name']?.toString() ?? ''),
                  trailing: Text(
                    '${b['available']} days',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.primary),
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.sectionGap),
            const SectionHeader('Apply for leave'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.cardPadding),
                child: Column(
                  children: [
                    DropdownButtonFormField<int>(
                      initialValue: _selectedTypeId,
                      decoration: const InputDecoration(labelText: 'Leave type'),
                      items: [
                        for (final t in ops.leaveTypes)
                          DropdownMenuItem(value: t['id'] as int, child: Text(t['name']?.toString() ?? '')),
                      ],
                      onChanged: (v) => setState(() => _selectedTypeId = v),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(onPressed: () => _pickDate(true), child: Text('From\n${_fmt(_start)}', textAlign: TextAlign.center)),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton(onPressed: () => _pickDate(false), child: Text('To\n${_fmt(_end)}', textAlign: TextAlign.center)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _reason,
                      decoration: const InputDecoration(labelText: 'Reason'),
                      maxLines: 3,
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: _selectedTypeId == null || _reason.text.isEmpty
                            ? null
                            : () async {
                                final ok = await ops.applyLeave(
                                  leaveTypeId: _selectedTypeId!,
                                  startDate: _start.toString().substring(0, 10),
                                  endDate: _end.toString().substring(0, 10),
                                  reason: _reason.text,
                                );
                                if (ok && mounted) {
                                  _reason.clear();
                                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Leave applied')));
                                }
                              },
                        child: const Text('Submit application'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.sectionGap),
            const SectionHeader('My applications'),
            ...ops.leaveApplications.map(
              (a) => Card(
                child: ListTile(
                  title: Text(a['leave_type_name']?.toString() ?? ''),
                  subtitle: Text('${a['start_date']} → ${a['end_date']}'),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: _statusColor(a['status']?.toString()).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      a['status']?.toString() ?? '',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: _statusColor(a['status']?.toString())),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Future<void> _pickDate(bool isStart) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: isStart ? _start : _end,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _start = picked;
        } else {
          _end = picked;
        }
      });
    }
  }
}
