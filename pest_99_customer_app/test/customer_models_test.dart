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

  test('CustomerBooking isPaid does not match Unpaid', () {
    final unpaid = CustomerBooking.fromJson({
      'id': 1,
      'service_type': 'General Pest',
      'payment_status': 'Unpaid',
    });
    final pending = CustomerBooking.fromJson({
      'id': 2,
      'service_type': 'General Pest',
      'payment_status': 'Pending',
      'price_confirmation_pending': true,
    });
    final paid = CustomerBooking.fromJson({
      'id': 3,
      'service_type': 'General Pest',
      'payment_status': 'Paid',
    });
    expect(unpaid.isPaid, isFalse);
    expect(unpaid.paymentStatusLabel, 'Unpaid');
    expect(pending.isPaid, isFalse);
    expect(pending.paymentStatusLabel, 'Price Confirmation Pending');
    expect(paid.isPaid, isTrue);
    expect(paid.paymentStatusLabel, 'Paid');
  });

  test('CustomerBooking shows technician status after accept', () {
    final booking = CustomerBooking.fromJson({
      'id': 4,
      'service_type': 'General Pest',
      'status': 'Pending',
      'partner_status': 'accepted',
      'payment_status': 'Unpaid',
      'technician_name': 'Ravi Tech',
      'technician_mobile': '9876543210',
      'can_cancel': true,
    });
    expect(booking.hasAssignedTechnician, isTrue);
    expect(booking.visitStatusLabel, 'Technician assigned');
    expect(booking.canCancel, isTrue);
    expect(booking.isPaid, isFalse);
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
