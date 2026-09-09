import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/bookings_provider.dart';
import '../../shared/widgets/profile_aware_top_bar.dart';
import '../../shared/booking_workflow.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/no_internet_view.dart';
import '../../shared/widgets/booking_cards.dart';

class BookingsScreen extends StatefulWidget {
  const BookingsScreen({super.key});

  @override
  State<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends State<BookingsScreen> {
  Timer? _syncTimer;

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

    final list = bookings.available;

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.screenEdge,
        AppSpacing.sectionGap,
        AppSpacing.screenEdge,
        100,
      ),
      children: [
        if (bookings.isSuspended) ...[
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF1F0),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFFFCCC7)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Account suspended',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: const Color(0xFFCF1322),
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  bookings.suspendMessage.isNotEmpty
                      ? bookings.suspendMessage
                      : 'New bookings are hidden until CRM reactivates your account.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFFA8071A),
                      ),
                ),
                if (bookings.suspendReason.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Reason: ${bookings.suspendReason}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: const Color(0xFF820014),
                        ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.elementGap),
        ],
        if (bookings.manualAssignOnly && !bookings.isSuspended) ...[
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
        const SizedBox(height: AppSpacing.sectionGap),
        if (list.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 48),
            child: Center(
              child: Text(
                bookings.isSuspended
                    ? 'No bookings available while suspended'
                    : bookings.manualAssignOnly
                        ? 'Nothing assigned to you yet'
                        : 'No new bookings right now',
              ),
            ),
          )
        else
          ...list.map((b) {
            final ui = BookingMapper.fromPartner(b);
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.elementGap),
              child: AvailableBookingCard(
                booking: ui,
                isAcceptLoading: bookings.isProcessing(b.id),
                isRejectLoading: bookings.isProcessing(b.id),
                onAccept: bookings.isProcessing(b.id)
                    ? null
                    : () => BookingWorkflow.accept(context, b.id),
                onReject: bookings.isProcessing(b.id)
                    ? null
                    : () => BookingWorkflow.reject(context, b.id),
              ),
            );
          }),
      ],
    );
  }
}
