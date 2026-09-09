import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/models/customer_models.dart';
import 'package:pest_99_customer_app/services/places_service.dart';
import 'package:pest_99_customer_app/widgets/service_address_section.dart';
import 'package:pest_99_customer_app/core/booking_timezone.dart';
import 'package:pest_99_customer_app/providers/booking_flow_provider.dart';

void main() {
  final cities = [
    const MasterCity(id: 1, name: 'Mumbai'),
    const MasterCity(id: 2, name: 'Navi Mumbai'),
    const MasterCity(id: 6, name: 'Pune'),
    const MasterCity(id: 5, name: 'Lonavla'),
    const MasterCity(id: 3, name: 'Thane'),
  ];

  test('matches Mumbai from locality even when city_hint is Konkan Division', () {
    const place = ResolvedPlace(
      formattedAddress: 'Dadar Railway Station, Dadar, Mumbai, Maharashtra',
      streetLine: 'Dadar Railway Station',
      latitude: 19.0197148,
      longitude: 72.8437936,
      locality: 'Mumbai',
      sublocality: 'Dadar',
      cityHint: 'Konkan Division', // production bug until deploy
    );
    expect(resolveCityIdFromPlace(place, cities), 1);
    expect(matchMasterCityId('Konkan Division', cities), isNull);
    expect(matchMasterCityId('Mumbai', cities), 1);
  });

  test('matches from formatted address when hints empty', () {
    const place = ResolvedPlace(
      formattedAddress: 'Something, Pune, Maharashtra',
      streetLine: 'Something',
      latitude: 18.5,
      longitude: 73.8,
    );
    expect(resolveCityIdFromPlace(place, cities), 6);
  });

  test('IST payload for 2:30 PM today wall clock', () {
    final date = DateTime(2026, 9, 5);
    expect(BookingTimezone.toIstIso8601(date, 14, 30), '2026-09-05T14:30:00+05:30');
    expect(BookingTimezone.bookingDate(date), '2026-09-05');
    expect(BookingTimezone.bookingTime24(14, 30), '14:30');
    expect(BookingTimezone.format12h(14, 30), '02:30 PM');
  });

  test('provider no longer defaults to tomorrow', () {
    final flow = BookingFlowProvider();
    final today = BookingTimezone.today();
    expect(flow.selectedDate.difference(today).inDays, 0);
  });

  test('clearLocationIds clears both city and location ids', () {
    final flow = BookingFlowProvider();
    flow.setServiceAddress(masterCityId: 1, city: 'Mumbai', masterLocationId: 99, area: 'Dadar');
    flow.setServiceAddress(clearLocationIds: true, address: 'new');
    expect(flow.masterCityId, isNull);
    expect(flow.masterLocationId, isNull);
    expect(flow.serviceArea, '');
  });

  test('formatSchedule displays IST not shifted local wrongly for +05:30 input', () {
    // Stored as UTC equivalent of 14:30 IST
    final shown = BookingTimezone.formatSchedule('2026-09-05T09:00:00Z', pattern: 'd MMM yyyy, h:mm a');
    expect(shown, '5 Sep 2026, 2:30 PM');
  });
}
