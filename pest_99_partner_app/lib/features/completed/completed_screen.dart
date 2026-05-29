import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/bookings_provider.dart';
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

    return Scaffold(
      appBar: const ProfileAwareTopBar(),
      body: RefreshIndicator(
        onRefresh: () => bookings.refreshListsLight(force: true),
        child: ListView(
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
                Text('Completed Jobs', style: Theme.of(context).textTheme.headlineSmall),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainerLow,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text('${bookings.completed.length} total'),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.elementGap),
            if (bookings.completed.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 48),
                child: Center(child: Text('No completed jobs yet')),
              )
            else
              ...bookings.completed.map(
                (b) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.elementGap),
                  child: CompletedBookingCard(booking: BookingMapper.fromPartner(b)),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
