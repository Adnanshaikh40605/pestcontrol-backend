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

    test('night slots are not bookable; daytime from 08:00 is', () {
      expect(BookingTimezone.isBookableTime(0, 0), isFalse);
      expect(BookingTimezone.isBookableTime(2, 0), isFalse);
      expect(BookingTimezone.isBookableTime(5, 30), isFalse);
      expect(BookingTimezone.isBookableTime(7, 59), isFalse);
      expect(BookingTimezone.isBookableTime(8, 0), isTrue);
      expect(BookingTimezone.isBookableTime(9, 0), isTrue);
      expect(BookingTimezone.isBookableTime(14, 0), isTrue);
      expect(BookingTimezone.coerceBookableTime(2, 0), (8, 0));
      expect(BookingTimezone.coerceBookableTime(7, 59), (8, 0));
      expect(BookingTimezone.coerceBookableTime(9, 15), (9, 15));
    });

    test('defaultPreferredDateTime: midnight and early morning → 8:00 AM', () {
      for (final now in [
        DateTime(2026, 9, 16, 0, 0),
        DateTime(2026, 9, 16, 2, 0),
        DateTime(2026, 9, 16, 5, 30),
        DateTime(2026, 9, 16, 7, 59),
      ]) {
        final target = BookingTimezone.defaultPreferredDateTime(now);
        expect(target.year, 2026);
        expect(target.month, 9);
        expect(target.day, 16);
        expect(target.hour, 8);
        expect(target.minute, 0);
      }
    });

    test('defaultPreferredDateTime: 8:00 → 9:00; 9:00 → 10:00; afternoon +1h', () {
      expect(
        BookingTimezone.defaultPreferredDateTime(DateTime(2026, 9, 16, 8, 0)),
        DateTime(2026, 9, 16, 9, 0),
      );
      expect(
        BookingTimezone.defaultPreferredDateTime(DateTime(2026, 9, 16, 9, 0)),
        DateTime(2026, 9, 16, 10, 0),
      );
      expect(
        BookingTimezone.defaultPreferredDateTime(DateTime(2026, 9, 16, 14, 0)),
        DateTime(2026, 9, 16, 15, 0),
      );
    });

    test('defaultPreferredDateTime: late evening bump to next-day 8:00', () {
      final target =
          BookingTimezone.defaultPreferredDateTime(DateTime(2026, 9, 16, 23, 30));
      expect(target, DateTime(2026, 9, 17, 8, 0));
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
      final parts = flow.preferredTimeParts!;
      expect(BookingTimezone.isBookableTime(parts.$1, parts.$2), isTrue);
    });

    test('setPreferredTime updates 12h label and 24h payload', () {
      final flow = BookingFlowProvider();
      flow.setPreferredTime(14, 30);
      expect(flow.preferredTime, '02:30 PM');
      expect(flow.bookingTime24, '14:30');
      expect(BookingFlowProvider.formatFriendlyTime(flow.preferredTime), '2:30 pm');
    });

    test('setPreferredTime coerces night times to 8:00 AM', () {
      final flow = BookingFlowProvider();
      flow.setPreferredTime(2, 0);
      expect(flow.preferredTime, '08:00 AM');
      expect(flow.bookingTime24, '08:00');
      flow.setPreferredTime(7, 59);
      expect(flow.bookingTime24, '08:00');
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
