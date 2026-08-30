import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_partner_app/core/mappers/booking_mapper.dart';
import 'package:pest_99_partner_app/models/booking.dart';

void main() {
  group('BookingMapper.shortAreaLabel', () {
    test('uses locality + city from API fields', () {
      final b = PartnerBooking(
        id: 1,
        serviceType: 'Cockroach / Ants',
        localityName: 'Kondhwa',
        cityName: 'Pune',
        clientAddress: 'B8-503 R EUPHORIA OPP talab factory, Kondhwa, Pune, Maharashtra 411048, India',
        locationDisplay:
            'B8-503 R EUPHORIA OPP talab factory, Kondhwa, Pune, Maharashtra 411048, India',
      );
      expect(BookingMapper.shortAreaLabel(b), 'Kondhwa, Pune');
    });

    test('does not include flat or pin when guessing from long address', () {
      final b = PartnerBooking(
        id: 2,
        serviceType: 'Bed Bugs',
        clientAddress:
            'B8-503 R EUPHORIA OPP talab factory, Kondhwa, Pune, Maharashtra 411048, India',
      );
      final short = BookingMapper.shortAreaLabel(b);
      expect(short.toLowerCase().contains('411048'), isFalse);
      expect(short.toLowerCase().contains('india'), isFalse);
      expect(short.toLowerCase().contains('b8-503'), isFalse);
      expect(short.contains('Pune'), isTrue);
    });

    test('city only when locality missing', () {
      final b = PartnerBooking(
        id: 3,
        serviceType: 'Termite',
        cityName: 'Mumbai',
      );
      expect(BookingMapper.shortAreaLabel(b), 'Mumbai');
    });
  });
}
