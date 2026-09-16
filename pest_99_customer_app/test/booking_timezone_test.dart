import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/core/booking_timezone.dart';
import 'package:pest_99_customer_app/providers/booking_flow_provider.dart';

void main() {
  group('BookingTimezone', () {
    test('today is date-only without tomorrow offset', () {
      final today = BookingTimezone.today();
      final now = BookingTimezone.now();
      expect(today.year, now.year);
      expect(today.month, now.month);
      expect(today.day, now.day);
      expect(today.hour, 0);
      expect(today.minute, 0);
    });

    test('format12h converts 24h correctly', () {
      expect(BookingTimezone.format12h(14, 30), '02:30 PM');
      expect(BookingTimezone.format12h(10, 0), '10:00 AM');
      expect(BookingTimezone.format12h(0, 15), '12:15 AM');
      expect(BookingTimezone.format12h(12, 0), '12:00 PM');
    });

    test('toIstIso8601 keeps wall clock with +05:30', () {
      final iso = BookingTimezone.toIstIso8601(DateTime(2026, 9, 5), 14, 30);
      expect(iso, '2026-09-05T14:30:00+05:30');
    });

    test('bookingDate and bookingTime24 are standardized', () {
      expect(BookingTimezone.bookingDate(DateTime(2026, 9, 5)), '2026-09-05');
      expect(BookingTimezone.bookingTime24(14, 30), '14:30');
    });
  });

  group('BookingFlowProvider schedule defaults', () {
    test('preferred date defaults to today or tomorrow when now+1h crosses midnight', () {
      final flow = BookingFlowProvider();
      final today = BookingTimezone.today();
      final parsed = DateTime.parse(flow.preferredDate);
      final day = DateTime(parsed.year, parsed.month, parsed.day);
      final diff = day.difference(today).inDays;
      expect(diff == 0 || diff == 1, isTrue);
      expect(flow.preferredTime, isNotEmpty);
      expect(flow.bookingTime24, isNotNull);
    });

    test('setPreferredTime updates 12h label and 24h payload', () {
      final flow = BookingFlowProvider();
      flow.setPreferredTime(14, 30);
      expect(flow.preferredTime, '02:30 PM');
      expect(flow.bookingTime24, '14:30');
      expect(BookingFlowProvider.formatFriendlyTime(flow.preferredTime), '2:30 pm');
    });

    test('setServiceAddress clearLocationIds clears masterLocationId field', () {
      final flow = BookingFlowProvider();
      flow.setServiceAddress(masterCityId: 1, masterLocationId: 2, area: 'Dadar', city: 'Mumbai');
      flow.setServiceAddress(clearLocationIds: true);
      expect(flow.masterCityId, isNull);
      expect(flow.masterLocationId, isNull);
      expect(flow.serviceArea, isEmpty);
    });
  });
}
