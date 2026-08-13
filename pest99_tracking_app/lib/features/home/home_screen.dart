import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/app_providers.dart';
import '../../providers/operations_provider.dart';
import '../../shared/widgets/section_header.dart';
import '../../shared/widgets/stat_tile.dart';
import '../../shared/widgets/status_chip.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>(() => context.read<TrackingProvider>().refreshStatus());
  }

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  String _formatTime(dynamic v) {
    if (v == null) return '—';
    try {
      return DateFormat('h:mm a').format(DateTime.parse(v.toString()).toLocal());
    } catch (_) {
      return '—';
    }
  }

  String _formatDuration(int? minutes) {
    if (minutes == null || minutes <= 0) return '—';
    final h = minutes ~/ 60;
    final m = minutes % 60;
    if (h == 0) return '${m}m';
    return '${h}h ${m}m';
  }

  String _relativePing(dynamic v) {
    if (v == null) return '';
    try {
      final diff = DateTime.now().difference(DateTime.parse(v.toString()).toLocal());
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes} min ago';
      return '${diff.inHours} hr ago';
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final tracking = context.watch<TrackingProvider>();
    final ops = context.read<OperationsProvider>();
    final me = tracking.me;
    final profile = me?['profile'] as Map<String, dynamic>?;
    final settings = me?['settings'] as Map<String, dynamic>?;
    final session = me?['active_session'] as Map<String, dynamic>?;
    final lastPing = me?['last_ping'] as Map<String, dynamic>?;
    final name = profile?['name']?.toString() ?? 'Staff';
    final city = profile?['city']?.toString() ?? '';
    final hasConsent = me?['has_consent'] == true;
    final checkedIn = tracking.isCheckedIn;
    final shiftStart = settings?['shift_start_time']?.toString() ?? '9:00';
    final shiftEnd = settings?['shift_end_time']?.toString() ?? '18:00';
    final distance = session?['total_distance_km']?.toString() ?? '0';
    final workingMin = session?['working_minutes'] as int?;
    final dateStr = DateFormat('EEE, d MMM').format(DateTime.now());

    return Scaffold(
      backgroundColor: AppColors.background,
      body: RefreshIndicator(
        onRefresh: tracking.refreshStatus,
        color: AppColors.primary,
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.screenEdge),
          children: [
            Text('$_greeting(), $name', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 4),
            Text(
              '$dateStr${city.isNotEmpty ? ' · $city' : ''}',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.sectionGap),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.cardPadding),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    checkedIn ? StatusChip.onDuty() : StatusChip.offDuty(),
                    const SizedBox(height: 12),
                    if (checkedIn) ...[
                      _infoRow(Icons.login_rounded, 'Checked in ${_formatTime(session?['check_in_at'])}'),
                      _infoRow(Icons.gps_fixed, 'GPS tracking on'),
                      if (lastPing?['battery_percent'] != null)
                        _infoRow(Icons.battery_full, '${lastPing!['battery_percent']}% battery'),
                      _infoRow(Icons.cloud_done, 'Synced'),
                    ] else ...[
                      Text('Shift: $shiftStart – $shiftEnd', style: Theme.of(context).textTheme.bodyMedium),
                      const SizedBox(height: 4),
                      Text('Not checked in', style: Theme.of(context).textTheme.labelSmall),
                    ],
                  ],
                ),
              ),
            ),
            if (tracking.error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(tracking.error!, style: const TextStyle(color: AppColors.danger, fontSize: 13)),
              ),
            ],
            const SizedBox(height: AppSpacing.sectionGap),
            if (!hasConsent)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.cardPadding),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.shield_outlined, color: AppColors.primary),
                          const SizedBox(width: 8),
                          Text('GPS Tracking Consent', style: Theme.of(context).textTheme.titleMedium),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Location is recorded only while you are checked in during working hours.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
                      ),
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: tracking.isLoading ? null : () => tracking.acceptConsent(),
                        child: const Text('I agree'),
                      ),
                    ],
                  ),
                ),
              ),
            if (hasConsent) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.cardPadding),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      FilledButton.icon(
                        onPressed: tracking.isLoading
                            ? null
                            : () async {
                                final ok = checkedIn ? await tracking.checkOut() : await tracking.checkIn();
                                if (ok && mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(checkedIn
                                          ? 'Checked out. GPS tracking stopped.'
                                          : 'Checked in at ${_formatTime(DateTime.now().toIso8601String())}'),
                                    ),
                                  );
                                }
                              },
                        icon: Icon(checkedIn ? Icons.logout : Icons.login),
                        label: Text(checkedIn ? 'Check out' : 'Check in'),
                        style: FilledButton.styleFrom(
                          backgroundColor: checkedIn ? AppColors.danger : AppColors.primary,
                        ),
                      ),
                      if (checkedIn) ...[
                        const SizedBox(height: 8),
                        Text(
                          checkedIn ? 'End shift and stop location tracking' : 'Start GPS tracking for your shift',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                      ] else
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            'Start GPS tracking for your shift',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.labelSmall,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              if (checkedIn) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () async {
                          if (await ops.startBreak() && mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Break started')));
                          }
                        },
                        icon: const Icon(Icons.free_breakfast_outlined, size: 18),
                        label: const Text('Start break'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () async {
                          if (await ops.endBreak() && mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Break ended')));
                          }
                        },
                        icon: const Icon(Icons.play_arrow_rounded, size: 18),
                        label: const Text('End break'),
                      ),
                    ),
                  ],
                ),
              ],
            ],
            const SizedBox(height: AppSpacing.sectionGap),
            const SectionHeader('Today summary'),
            Row(
              children: [
                StatTile(value: '$distance km', label: 'Distance'),
                const SizedBox(width: 12),
                StatTile(value: _formatDuration(workingMin), label: 'Hours'),
              ],
            ),
            if (checkedIn && lastPing?['recorded_at'] != null) ...[
              const SizedBox(height: 12),
              Text(
                'Last ping: ${_relativePing(lastPing!['recorded_at'])}',
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ],
            if (tracking.isLoading) ...[
              const SizedBox(height: 16),
              const LinearProgressIndicator(color: AppColors.primary),
            ],
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.successText),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }
}
