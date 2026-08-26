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
import '../../shared/widgets/app_snackbar.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/primary_button.dart';

class LeaveRequestsScreen extends StatefulWidget {
  const LeaveRequestsScreen({super.key});

  @override
  State<LeaveRequestsScreen> createState() => _LeaveRequestsScreenState();
}

class _LeaveRequestsScreenState extends State<LeaveRequestsScreen> {
  List<PartnerLeaveRequest> _items = [];
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
      final list = await EarningsService(context.read<ApiClient>()).listLeaveRequests();
      if (!mounted) return;
      setState(() {
        _items = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = userErrorMessage(e, fallback: 'Could not load leave requests.');
        _loading = false;
      });
    }
  }

  Future<void> _createLeave() async {
    final range = await showDateRangePicker(
      context: context,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDateRange: DateTimeRange(
        start: DateTime.now().add(const Duration(days: 1)),
        end: DateTime.now().add(const Duration(days: 2)),
      ),
    );
    if (range == null || !mounted) return;

    final reasonCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Leave reason'),
        content: TextField(
          controller: reasonCtrl,
          decoration: const InputDecoration(hintText: 'Optional reason'),
          maxLines: 3,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Submit')),
        ],
      ),
    );
    if (ok != true || !mounted) return;

    final fmt = DateFormat('yyyy-MM-dd');
    try {
      await EarningsService(context.read<ApiClient>()).createLeaveRequest(
        startDate: fmt.format(range.start),
        endDate: fmt.format(range.end),
        reason: reasonCtrl.text.trim(),
      );
      if (!mounted) return;
      AppSnackBar.success(context, 'Leave request submitted.');
      await _load();
    } catch (e) {
      if (!mounted) return;
      AppSnackBar.error(
        context,
        userErrorMessage(e, fallback: 'Could not submit leave.'),
      );
    }
  }

  Future<void> _cancel(PartnerLeaveRequest leave) async {
    try {
      await EarningsService(context.read<ApiClient>()).cancelLeaveRequest(leave.id);
      if (!mounted) return;
      await _load();
    } catch (e) {
      if (!mounted) return;
      AppSnackBar.error(
        context,
        userErrorMessage(e, fallback: 'Could not cancel leave request.'),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Leave requests'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _createLeave,
        icon: const Icon(Icons.add),
        label: const Text('Request leave'),
      ),
      body: _loading && _items.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _items.isEmpty
              ? AsyncErrorView(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: _items.isEmpty
                      ? ListView(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.all(AppSpacing.screenEdge),
                          children: [
                            const SizedBox(height: 48),
                            Icon(Icons.event_busy_outlined, size: 56, color: AppColors.textSecondary),
                            const SizedBox(height: 12),
                            Text(
                              'No leave requests yet',
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    color: AppColors.textSecondary,
                                  ),
                            ),
                            const SizedBox(height: 24),
                            PrimaryButton(label: 'Request leave', onPressed: _createLeave),
                          ],
                        )
                      : ListView.separated(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.fromLTRB(
                            AppSpacing.screenEdge,
                            AppSpacing.screenEdge,
                            AppSpacing.screenEdge,
                            100,
                          ),
                          itemCount: _items.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 10),
                          itemBuilder: (context, i) {
                            final leave = _items[i];
                            return Card(
                              child: ListTile(
                                title: Text('${leave.startDate} → ${leave.endDate}'),
                                subtitle: Text(
                                  [
                                    leave.status,
                                    if (leave.reason.isNotEmpty) leave.reason,
                                  ].join(' · '),
                                ),
                                trailing: leave.isPending
                                    ? TextButton(
                                        onPressed: () => _cancel(leave),
                                        child: const Text('Cancel'),
                                      )
                                    : null,
                              ),
                            );
                          },
                        ),
                ),
    );
  }
}
