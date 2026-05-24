import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/bookings_provider.dart';
import '../../shared/widgets/profile_aware_top_bar.dart';
import '../../shared/booking_workflow.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/booking_cards.dart';

class BookingsScreen extends StatefulWidget {
  const BookingsScreen({super.key});

  @override
  State<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends State<BookingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<BookingsProvider>().refreshAll();
    });
  }

  @override
  Widget build(BuildContext context) {
    final bookings = context.watch<BookingsProvider>();

    return Scaffold(
      appBar: const ProfileAwareTopBar(),
      body: RefreshIndicator(
        onRefresh: bookings.refreshAll,
        child: bookings.loading && bookings.available.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _buildBody(context, bookings),
      ),
    );
  }

  Widget _buildBody(BuildContext context, BookingsProvider bookings) {
    if (bookings.error != null && bookings.available.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: MediaQuery.sizeOf(context).height * 0.45,
            child: AsyncErrorView(
              message: bookings.error!,
              onRetry: bookings.refreshAll,
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
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('New Bookings', style: Theme.of(context).textTheme.headlineSmall),
            Text('${list.length} requests'),
          ],
        ),
        const SizedBox(height: AppSpacing.elementGap),
        if (list.isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 48),
            child: Center(child: Text('No new bookings right now')),
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
