import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/models/booking.dart';
import '../../core/theme/app_spacing.dart';
import '../../models/booking.dart' as api;
import '../../providers/bookings_provider.dart';
import '../../shared/widgets/profile_aware_top_bar.dart';
import '../../shared/booking_workflow.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/no_internet_view.dart';
import '../../shared/widgets/booking_cards.dart';
import '../../shared/widgets/booking_day_sections.dart';
import '../../shared/widgets/segmented_tabs.dart';

class BookingsScreen extends StatefulWidget {
  const BookingsScreen({super.key});

  @override
  State<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends State<BookingsScreen> {
  Timer? _syncTimer;
  /// 0 = Today, 1 = Tomorrow
  int _dayTabIndex = 0;

  @override
  void initState() {
    super.initState();
    _syncTimer = Timer.periodic(const Duration(seconds: 45), (_) {
      if (!mounted) return;
      context.read<BookingsProvider>().refreshListsLight();
    });
  }

  @override
  void dispose() {
    _syncTimer?.cancel();
    super.dispose();
  }

  String _emptyMessage(BookingsProvider bookings, {required bool isToday}) {
    if (bookings.isSuspended) {
      return 'No bookings available while suspended';
    }
    if (bookings.isOnLeave) {
      return 'No bookings available while you are on leave';
    }
    if (bookings.manualAssignOnly) {
      return 'Nothing assigned to you yet';
    }
    return isToday
        ? 'No bookings for today'
        : 'No bookings for tomorrow';
  }

  @override
  Widget build(BuildContext context) {
    final bookings = context.watch<BookingsProvider>();

    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: const ProfileAwareTopBar(),
      body: RefreshIndicator(
        onRefresh: () => bookings.refreshListsLight(force: true),
        child: bookings.loading && bookings.available.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _buildBody(context, bookings),
      ),
    );
  }

  Widget _buildBody(BuildContext context, BookingsProvider bookings) {
    if (bookings.error != null && bookings.available.isEmpty) {
      final offline = NoInternetView.isOfflineMessage(bookings.error);
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: MediaQuery.sizeOf(context).height * 0.55,
            child: offline
                ? NoInternetView(
                    onRetry: () => bookings.refreshListsLight(force: true),
                  )
                : AsyncErrorView(
                    message: bookings.error!,
                    onRetry: () => bookings.refreshListsLight(force: true),
                  ),
          ),
        ],
      );
    }

    final sections = BookingDaySections.from(bookings.available);
    final isTodayTab = _dayTabIndex == 0;
    final dayList = isTodayTab ? sections.today : sections.tomorrow;

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.screenEdge,
        AppSpacing.sectionGap,
        AppSpacing.screenEdge,
        100,
      ),
      children: [
        // On leave and suspended both hide the pool. Same banner, different
        // wording and colour, because one is temporary and one is a block.
        if (bookings.isUnavailable) ...[
          _UnavailableBanner(
            onLeave: bookings.isOnLeave,
            message: bookings.suspendMessage,
            reason: bookings.suspendReason,
          ),
          const SizedBox(height: AppSpacing.elementGap),
        ],
        if (bookings.manualAssignOnly && !bookings.isUnavailable) ...[
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFFFBE6),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFFFE58F)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Office assigns your jobs',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: const Color(0xFFAD6800),
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  bookings.manualAssignMessage.isNotEmpty
                      ? bookings.manualAssignMessage
                      : 'New bookings are assigned to you by the office. '
                          'Check the Accepted tab for your jobs.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFF874D00),
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.elementGap),
        ],
        Text(
          'New Bookings',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
                color: const Color(0xFF111827),
              ),
        ),
        const SizedBox(height: 6),
        Text(
          "Switch between Today and Tomorrow to see that day's jobs.",
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: const Color(0xFF6B7280),
              ),
        ),
        const SizedBox(height: AppSpacing.sectionGap),
        SegmentedTabs(
          labels: [
            'Today (${sections.today.length})',
            'Tomorrow (${sections.tomorrow.length})',
          ],
          selectedIndex: _dayTabIndex,
          onChanged: (index) {
            if (index == _dayTabIndex) return;
            setState(() => _dayTabIndex = index);
          },
        ),
        const SizedBox(height: AppSpacing.sectionGap),
        ...buildSingleDayBookingChildren(
          bookings: dayList,
          emptyMessage: _emptyMessage(bookings, isToday: isTodayTab),
          cardBuilder: (b, ui) => _availableCard(context, bookings, b, ui),
        ),
        // Keep beyond-tomorrow jobs visible, but outside the two day tabs.
        if (sections.later.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sectionGap),
          BookingSectionHeader(
            title: 'Later',
            count: sections.later.length,
          ),
          ...buildSingleDayBookingChildren(
            bookings: sections.later,
            cardBuilder: (b, ui) => _availableCard(context, bookings, b, ui),
          ),
        ],
      ],
    );
  }

  Widget _availableCard(
    BuildContext context,
    BookingsProvider bookings,
    api.PartnerBooking b,
    Booking ui,
  ) {
    final processing = bookings.isProcessing(b.id);
    return AvailableBookingCard(
      booking: ui,
      isAcceptLoading: processing,
      isRejectLoading: processing,
      onAccept: processing ? null : () => BookingWorkflow.accept(context, b.id),
      onReject: processing ? null : () => BookingWorkflow.reject(context, b.id),
    );
  }
}

/// Explains why the booking pool is empty when the office has marked this
/// technician on leave or suspended.
class _UnavailableBanner extends StatelessWidget {
  const _UnavailableBanner({
    required this.onLeave,
    required this.message,
    required this.reason,
  });

  final bool onLeave;
  final String message;
  final String reason;

  @override
  Widget build(BuildContext context) {
    final background = onLeave ? const Color(0xFFFFFBE6) : const Color(0xFFFFF1F0);
    final border = onLeave ? const Color(0xFFFFE58F) : const Color(0xFFFFCCC7);
    final title = onLeave ? const Color(0xFFAD6800) : const Color(0xFFCF1322);
    final body = onLeave ? const Color(0xFF874D00) : const Color(0xFFA8071A);
    final detail = onLeave ? const Color(0xFF613400) : const Color(0xFF820014);

    final fallback = onLeave
        ? 'You are marked as on leave, so new bookings are not being sent to you.'
        : 'New bookings are hidden until CRM reactivates your account.';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            onLeave ? 'You are on leave' : 'Account suspended',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: title,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            message.isNotEmpty ? message : fallback,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: body),
          ),
          // The server already folds the reason into `message`; show it on its
          // own only when it did not.
          if (reason.isNotEmpty && !message.contains(reason)) ...[
            const SizedBox(height: 6),
            Text(
              'Reason: $reason',
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: detail),
            ),
          ],
          const SizedBox(height: 6),
          Text(
            'Your status is set by the office. Contact CRM admin for changes.',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: detail),
          ),
        ],
      ),
    );
  }
}
