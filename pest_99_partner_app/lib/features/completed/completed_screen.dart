import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../models/booking.dart' as api;
import '../../core/theme/app_spacing.dart';
import '../../providers/bookings_provider.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/no_internet_view.dart';
import '../../shared/widgets/profile_aware_top_bar.dart';
import '../../shared/widgets/booking_cards.dart';
import '../../shared/widgets/call_sections.dart';

class CompletedScreen extends StatefulWidget {
  const CompletedScreen({super.key});

  @override
  State<CompletedScreen> createState() => _CompletedScreenState();
}

class _CompletedScreenState extends State<CompletedScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<BookingsProvider>().refreshListsLight();
    });
  }

  @override
  Widget build(BuildContext context) {
    final bookings = context.watch<BookingsProvider>();
    final completed = bookings.completed;
    final split = CallKindSplit.from(completed);

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
                      ..._completedSections(split),
                    ],
                  ),
      ),
    );
  }

  List<Widget> _completedSections(CallKindSplit split) {
    List<Widget> cards(List<api.PartnerBooking> rows) {
      return rows.map((raw) {
        final ui = BookingMapper.fromPartner(raw);
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.elementGap),
          child: CompletedBookingCard(booking: ui),
        );
      }).toList();
    }

    List<Widget> section(
      String title,
      List<api.PartnerBooking> rows,
      String subtitle,
      Color color,
    ) {
      return [
        CallSectionHeader(
          title: title,
          count: rows.length,
          subtitle: subtitle,
          color: color,
        ),
        if (rows.isEmpty)
          const Padding(
            padding: EdgeInsets.only(bottom: AppSpacing.sectionGap),
            child: Text(
              'None yet',
              style: TextStyle(color: Color(0xFF6B7280), fontWeight: FontWeight.w600),
            ),
          )
        else
          ...cards(rows),
        const SizedBox(height: AppSpacing.elementGap),
      ];
    }

    return [
      ...section(
        'Service Calls',
        split.serviceCalls,
        '₹300 recorded for each completed service call',
        const Color(0xFF7C3AED),
      ),
      ...section(
        'Complaint Calls',
        split.complaintCalls,
        'Complaint visits stay separate and do not earn ₹300',
        const Color(0xFFDC2626),
      ),
      if (split.other.isNotEmpty) ...[
        Text(
          'Other jobs (${split.other.length})',
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
        ),
        const SizedBox(height: AppSpacing.elementGap),
        ...cards(split.other),
      ] else if (split.isEmpty)
        const Padding(
          padding: EdgeInsets.only(top: 12),
          child: Text('No completed jobs yet'),
        ),
    ];
  }
}
