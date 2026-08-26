import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/utils/money_format.dart';
import '../../providers/bookings_provider.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/no_internet_view.dart';
import '../../shared/widgets/profile_aware_top_bar.dart';
import '../../shared/widgets/booking_cards.dart';

class CompletedScreen extends StatefulWidget {
  const CompletedScreen({super.key});

  @override
  State<CompletedScreen> createState() => _CompletedScreenState();
}

class _CompletedScreenState extends State<CompletedScreen> {
  @override
  Widget build(BuildContext context) {
    final bookings = context.watch<BookingsProvider>();
    final completed = bookings.completed;
    final uiBookings = completed.map(BookingMapper.fromPartner).toList();
    final yourShareTotal = MoneyFormat.sumRupees(
      uiBookings.where((b) => b.hasRevenuePayout).map((b) => b.yourShareAmount),
    );
    final earningJobs = uiBookings.where((b) => b.hasRevenuePayout).length;

    return Scaffold(
      appBar: const ProfileAwareTopBar(),
      body: RefreshIndicator(
        onRefresh: () => bookings.refreshListsLight(force: true),
        child: bookings.loading && completed.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : bookings.error != null && completed.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      SizedBox(
                        height: MediaQuery.sizeOf(context).height * 0.55,
                        child: NoInternetView.isOfflineMessage(bookings.error)
                            ? NoInternetView(
                                onRetry: () =>
                                    bookings.refreshListsLight(force: true),
                              )
                            : AsyncErrorView(
                                message: bookings.error!,
                                onRetry: () =>
                                    bookings.refreshListsLight(force: true),
                              ),
                      ),
                    ],
                  )
                : ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.screenEdge,
                      AppSpacing.sectionGap,
                      AppSpacing.screenEdge,
                      100,
                    ),
                    children: [
                      Text(
                        'Completed Jobs',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: AppSpacing.elementGap),
                      _ProgressBanner(
                        jobsDone: completed.length,
                        earningJobs: earningJobs,
                        yourShareTotal: yourShareTotal,
                      ),
                      const SizedBox(height: AppSpacing.sectionGap),
                      if (completed.isEmpty)
                        const Padding(
                          padding: EdgeInsets.only(top: 48),
                          child: Center(child: Text('No completed jobs yet')),
                        )
                      else
                        ...uiBookings.map(
                          (b) => Padding(
                            padding: const EdgeInsets.only(
                              bottom: AppSpacing.elementGap,
                            ),
                            child: CompletedBookingCard(booking: b),
                          ),
                        ),
                    ],
                  ),
      ),
    );
  }
}

class _ProgressBanner extends StatelessWidget {
  const _ProgressBanner({
    required this.jobsDone,
    required this.earningJobs,
    required this.yourShareTotal,
  });

  final int jobsDone;
  final int earningJobs;
  final String yourShareTotal;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Your progress',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: AppColors.primary,
                ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _ProgressStat(
                  value: '$jobsDone',
                  label: 'Jobs done',
                ),
              ),
              Container(width: 1, height: 36, color: AppColors.border),
              Expanded(
                child: _ProgressStat(
                  value: yourShareTotal,
                  label: 'Your share (40%)',
                ),
              ),
              Container(width: 1, height: 36, color: AppColors.border),
              Expanded(
                child: _ProgressStat(
                  value: '$earningJobs',
                  label: 'Paid services',
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'Amounts below are your technician share only — not the full customer job price.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

class _ProgressStat extends StatelessWidget {
  const _ProgressStat({required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: AppColors.textSecondary,
              ),
        ),
      ],
    );
  }
}
