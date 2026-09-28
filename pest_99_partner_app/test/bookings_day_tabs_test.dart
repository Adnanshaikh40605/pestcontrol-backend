import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_partner_app/core/schedule_day.dart';
import 'package:pest_99_partner_app/models/booking.dart';
import 'package:pest_99_partner_app/shared/widgets/booking_cards.dart';
import 'package:pest_99_partner_app/shared/widgets/booking_day_sections.dart';
import 'package:pest_99_partner_app/shared/widgets/segmented_tabs.dart';

void main() {
  final screenshotIst = DateTime.utc(2026, 9, 28, 9, 58);

  testWidgets('Tomorrow tab switches the list copy', (tester) async {
    final tabs = NewBookingDayTab();
    await tester.pumpWidget(
      MaterialApp(
        home: StatefulBuilder(
          builder: (context, setState) {
            final today = tabs.index == 0;
            return Scaffold(
              body: Column(
                children: [
                  SegmentedTabs(
                    labels: const ['Today (0)', 'Tomorrow (0)'],
                    selectedIndex: tabs.index,
                    onChanged: (index) {
                      if (!tabs.select(index)) return;
                      setState(() {});
                    },
                  ),
                  Text(today ? 'No bookings for today' : 'No bookings for tomorrow'),
                ],
              ),
            );
          },
        ),
      ),
    );

    expect(find.text('No bookings for today'), findsOneWidget);
    tabs.applyHint(0, 1);
    await tester.tap(find.text('Tomorrow (0)'));
    await tester.pump();
    expect(find.text('No bookings for tomorrow'), findsOneWidget);
    expect(tabs.index, 1);

    // A rebuild that still carries the old Today hint must not snap back.
    expect(tabs.applyHint(0, 1), isFalse);
    expect(tabs.index, 1);
    expect(find.text('No bookings for tomorrow'), findsOneWidget);
  });

  testWidgets('empty today stays a short line when Later has a job', (tester) async {
    final job = PartnerBooking(
      id: 3860,
      serviceType: 'Cockroach Standard',
      scheduleDatetime: '2026-09-30T07:30:00+00:00',
      timeSlot: '01:00 PM',
      price: '1600.00',
      localityName: 'Vikhroli East',
      cityName: 'Mumbai',
    );
    final sections = BookingDaySections.from([job], now: screenshotIst);
    expect(sections.today, isEmpty);
    expect(sections.later.map((b) => b.id), [3860]);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ListView(
            children: [
              ...buildSingleDayBookingChildren(
                bookings: sections.today,
                emptyMessage: 'No bookings for today',
                compactEmpty: true,
                cardBuilder: (_, _) => const SizedBox.shrink(),
              ),
              ...buildSingleDayBookingChildren(
                bookings: sections.later,
                cardBuilder: (raw, ui) => AvailableBookingCard(
                  booking: ui,
                  onAccept: () {},
                  onReject: () {},
                ),
              ),
            ],
          ),
        ),
      ),
    );

    final empty = tester.widget<Padding>(find.byKey(const Key('single-day-empty')));
    expect(empty.padding, const EdgeInsets.only(top: 2, bottom: 2));
    expect(find.text('No bookings for today'), findsOneWidget);
    expect(find.text('Wed, 30 Sep'), findsOneWidget);
    expect(find.text('01:00 PM'), findsOneWidget);
    expect(find.text('Accept Job'), findsOneWidget);
    expect(find.text('Reject'), findsOneWidget);
  });
}
