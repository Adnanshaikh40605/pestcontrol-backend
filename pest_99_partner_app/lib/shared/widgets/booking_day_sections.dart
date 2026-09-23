import 'package:flutter/material.dart';

import '../../core/mappers/booking_mapper.dart';
import '../../core/models/booking.dart';
import '../../core/theme/app_spacing.dart';
import '../../models/booking.dart' as api;

/// Split partner bookings into Today / Tomorrow / Later for list UIs.
class BookingDaySections {
  BookingDaySections({
    required this.today,
    required this.tomorrow,
    required this.later,
  });

  final List<api.PartnerBooking> today;
  final List<api.PartnerBooking> tomorrow;
  final List<api.PartnerBooking> later;

  factory BookingDaySections.from(List<api.PartnerBooking> raw) {
    final today = <api.PartnerBooking>[];
    final tomorrow = <api.PartnerBooking>[];
    final later = <api.PartnerBooking>[];
    for (final b in raw) {
      final ui = BookingMapper.fromPartner(b);
      switch (ui.dayBucket) {
        case 'today':
          today.add(b);
        case 'tomorrow':
          tomorrow.add(b);
        default:
          later.add(b);
      }
    }
    return BookingDaySections(today: today, tomorrow: tomorrow, later: later);
  }

  bool get isEmpty => today.isEmpty && tomorrow.isEmpty && later.isEmpty;
}

class BookingSectionHeader extends StatelessWidget {
  const BookingSectionHeader({
    super.key,
    required this.title,
    required this.count,
  });

  final String title;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.elementGap, top: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: const Color(0xFF111827),
                  ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFF3F4F6),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: const Color(0xFFE5E7EB)),
            ),
            child: Text(
              '$count',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: const Color(0xFF374151),
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Builds sectioned children for a ListView. [cardBuilder] renders each booking.
List<Widget> buildDaySectionedBookingChildren({
  required List<api.PartnerBooking> bookings,
  required Widget Function(api.PartnerBooking raw, Booking ui) cardBuilder,
  String emptyMessage = 'No bookings',
}) {
  final sections = BookingDaySections.from(bookings);
  if (sections.isEmpty) {
    return [
      Padding(
        padding: const EdgeInsets.only(top: 48),
        child: Center(child: Text(emptyMessage)),
      ),
    ];
  }

  final out = <Widget>[];
  void addSection(String title, List<api.PartnerBooking> list) {
    if (list.isEmpty) return;
    out.add(BookingSectionHeader(title: title, count: list.length));
    for (final raw in list) {
      final ui = BookingMapper.fromPartner(raw);
      out.add(
        Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.elementGap),
          child: cardBuilder(raw, ui),
        ),
      );
    }
  }

  addSection("Today's Bookings", sections.today);
  addSection("Tomorrow's Bookings", sections.tomorrow);
  addSection('Later', sections.later);
  return out;
}

/// Builds list children for a single day bucket (no section header).
List<Widget> buildSingleDayBookingChildren({
  required List<api.PartnerBooking> bookings,
  required Widget Function(api.PartnerBooking raw, Booking ui) cardBuilder,
  String emptyMessage = 'No bookings',
}) {
  if (bookings.isEmpty) {
    return [
      Padding(
        padding: const EdgeInsets.only(top: 48),
        child: Center(child: Text(emptyMessage)),
      ),
    ];
  }

  return [
    for (final raw in bookings)
      Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.elementGap),
        child: cardBuilder(raw, BookingMapper.fromPartner(raw)),
      ),
  ];
}
