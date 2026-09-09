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

    test('past times on today are rejected', () {
      final today = BookingTimezone.today();
      expect(BookingTimezone.isNotInPast(today, 0, 0), isFalse);
      final tomorrow = today.add(const Duration(days: 1));
      expect(BookingTimezone.isNotInPast(tomorrow, 10, 0), isTrue);
    });
  });

  group('BookingFlowProvider date defaults', () {
    test('defaults selected date to today (IST)', () {
      final flow = BookingFlowProvider();
      final today = BookingTimezone.today();
      expect(flow.selectedDate.year, today.year);
      expect(flow.selectedDate.month, today.month);
      expect(flow.selectedDate.day, today.day);
      expect(flow.selectedSlot, isNotEmpty);
    });

    test('setTime updates 12h label', () {
      final flow = BookingFlowProvider();
      flow.setTime(14, 30);
      expect(flow.selectedHour, 14);
      expect(flow.selectedMinute, 30);
      expect(flow.selectedSlot, '02:30 PM');
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
