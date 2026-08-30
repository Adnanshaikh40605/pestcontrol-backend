import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../core/theme/app_spacing.dart';
import '../../models/booking.dart' as api;
import '../../providers/bookings_provider.dart';
import '../../core/booking_contact_actions.dart';
import '../../shared/booking_workflow.dart';
import '../../shared/widgets/app_snackbar.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/no_internet_view.dart';
import '../../shared/widgets/profile_aware_top_bar.dart';
import '../../shared/widgets/booking_cards.dart';

class AcceptedScreen extends StatefulWidget {
  const AcceptedScreen({super.key});

  @override
  State<AcceptedScreen> createState() => _AcceptedScreenState();
}

class _AcceptedScreenState extends State<AcceptedScreen> {
  Future<void> _call(BuildContext context, api.PartnerBooking raw) async {
    final ok = await BookingContactActions.callPhone(raw.clientMobile);
    if (!context.mounted) return;
    if (!ok) {
      AppSnackBar.error(context, 'Cannot call — phone number not available');
    }
  }

  Future<void> _maps(BuildContext context, api.PartnerBooking raw) async {
    final address = raw.locationDisplay ?? raw.clientAddress;
    final ok = await BookingContactActions.openMaps(address);
    if (!context.mounted) return;
    if (!ok) {
      AppSnackBar.error(context, 'Cannot open maps — address missing');
    }
  }

  void _onPrimary(BuildContext context, api.PartnerBooking raw) {
    final provider = context.read<BookingsProvider>();
    if (provider.isProcessing(raw.id)) return;
    BookingWorkflow.handleAcceptedPrimary(context, raw);
  }

  @override
  Widget build(BuildContext context) {
    final bookings = context.watch<BookingsProvider>();

    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: const ProfileAwareTopBar(),
      body: RefreshIndicator(
        onRefresh: () => bookings.refreshListsLight(force: true),
        child: bookings.loading && bookings.accepted.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : bookings.error != null && bookings.accepted.isEmpty
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
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Accepted Jobs',
                                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                        fontWeight: FontWeight.w800,
                                        color: const Color(0xFF111827),
                                      ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Jobs you’ve accepted and are working on',
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                        color: const Color(0xFF6B7280),
                                      ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 10),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF3F4F6),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(color: const Color(0xFFE5E7EB)),
                            ),
                            child: Text(
                              '${bookings.accepted.length} active',
                              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                    color: const Color(0xFF374151),
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.sectionGap),
                      if (bookings.accepted.isEmpty)
                        const Padding(
                          padding: EdgeInsets.only(top: 48),
                          child: Center(child: Text('No accepted jobs yet')),
                        )
                      else
                        ...bookings.accepted.map((raw) {
                          final ui = BookingMapper.fromPartner(raw);
                          final processing = bookings.isProcessing(raw.id);
                          final label = bookings.processingLabel(raw.id);

                          return Padding(
                            padding: const EdgeInsets.only(bottom: AppSpacing.elementGap),
                            child: AcceptedBookingCard(
                              booking: ui,
                              onViewDetails: processing
                                  ? null
                                  : () => context.push('/booking/${raw.id}'),
                              onCall: processing || !raw.canViewClientPhone
                                  ? null
                                  : () => _call(context, raw),
                              onMaps: processing
                                  ? null
                                  : () => _maps(context, raw),
                              onPrimaryAction:
                                  (raw.allowsStart || raw.allowsComplete)
                                      ? () => _onPrimary(context, raw)
                                      : null,
                              isPrimaryLoading: processing,
                              primaryLoadingLabel: label,
                            ),
                          );
                        }),
                    ],
                  ),
      ),
    );
  }
}
