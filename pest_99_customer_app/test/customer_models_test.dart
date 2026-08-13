import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/models/customer_models.dart';

void main() {
  test('CatalogRate parses package tiers', () {
    final rate = CatalogRate.fromJson({
      'id': 1,
      'service_package': 'General Pest',
      'plan_type': 'One Time Service',
      'area_key': '1 BHK',
      'amount': '1000.00',
      'package_tiers': {'standard': '1000.00', 'premium': '1150.00'},
      'region_name': 'Mumbai',
    });
    expect(rate.standardAmount, '1000.00');
    expect(rate.premiumAmount, '1150.00');
  });

  test('CustomerBooking parses rating flags', () {
    final booking = CustomerBooking.fromJson({
      'id': 9,
      'code': 'JC-9',
      'service_type': 'General Pest',
      'status': 'Done',
      'payment_status': 'Paid',
      'can_rate': true,
      'invoice_amount': '1000.00',
    });
    expect(booking.isDone, isTrue);
    expect(booking.isPaid, isTrue);
    expect(booking.canRate, isTrue);
  });

  test('CustomerProfile fromJson', () {
    final p = CustomerProfile.fromJson({
      'id': 1,
      'full_name': 'Ada',
      'mobile': '9999999999',
      'email': 'a@b.c',
      'client_id': 5,
    });
    expect(p.fullName, 'Ada');
    expect(p.clientId, 5);
  });

  test('AmcScheduleGroup parses parent and visits', () {
    final group = AmcScheduleGroup.fromJson({
      'parent': {
        'id': 1,
        'code': 'JC-1',
        'service_type': 'AMC Pest',
        'status': 'Pending',
      },
      'visits': [
        {
          'id': 2,
          'code': 'JC-2',
          'service_type': 'AMC Pest',
          'status': 'Upcoming',
          'schedule_datetime': '2026-08-01T10:00:00Z',
        },
      ],
    });
    expect(group.parent.id, 1);
    expect(group.visits, hasLength(1));
    expect(group.visits.first.id, 2);
  });
}
