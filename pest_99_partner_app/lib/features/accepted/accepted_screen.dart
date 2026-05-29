import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../core/theme/app_spacing.dart';
import '../../models/booking.dart' as api;
import '../../providers/bookings_provider.dart';
import '../../core/booking_contact_actions.dart';
import '../../shared/booking_workflow.dart';
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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cannot call — phone number not available')),
      );
    }
  }

  Future<void> _maps(BuildContext context, api.PartnerBooking raw) async {
    final address = raw.locationDisplay ?? raw.clientAddress;
    final ok = await BookingContactActions.openMaps(address);
    if (!context.mounted) return;
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cannot open maps — address missing')),
      );
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
      appBar: const ProfileAwareTopBar(),
      body: RefreshIndicator(
        onRefresh: () => bookings.refreshListsLight(force: true),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.screenEdge,
            16,
            AppSpacing.screenEdge,
            100,
          ),
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Accepted Jobs', style: Theme.of(context).textTheme.headlineSmall),
                Text('${bookings.accepted.length} active'),
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
                  padding: const EdgeInsets.only(bottom: 24),
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
                    onPrimaryAction: (raw.allowsStart || raw.allowsComplete)
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
