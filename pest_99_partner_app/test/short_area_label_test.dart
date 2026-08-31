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

  group('BookingMapper.fromPartner completed fields', () {
    test('maps completed_at to completionDate', () {
      final b = PartnerBooking(
        id: 469,
        serviceType: 'Cockroach / Ants',
        clientName: 'Adnan Shaikh',
        scheduleDatetime: '2026-05-20T10:00:00Z',
        completedAt: '2026-05-27T14:30:00Z',
        paymentStatus: 'Paid',
        paymentModel: 'revenue_sharing',
        visitPayoutAmount: '1800.00',
        technicianSharePercent: '40.00',
        payoutStatus: 'pending',
      );
      final ui = BookingMapper.fromPartner(b);
      expect(ui.completionDate, 'Wed, 27 May');
      expect(ui.customerName, 'Adnan Shaikh');
      expect(ui.isPaid, isTrue);
      expect(ui.hasRevenuePayout, isTrue);
      expect(ui.yourShareAmount, '1800.00');
    });

    test('falls back to schedule date when completed_at missing', () {
      final b = PartnerBooking(
        id: 1,
        serviceType: 'General Pest',
        scheduleDatetime: '2026-05-20T10:00:00Z',
      );
      final ui = BookingMapper.fromPartner(b);
      expect(ui.completionDate, isNotNull);
      expect(ui.completionDate, isNot(equals('—')));
    });
  });
}
