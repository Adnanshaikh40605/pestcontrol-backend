import 'package:flutter_test/flutter_test.dart';

import 'package:pest_99_partner_app/models/booking.dart';
import 'package:pest_99_partner_app/models/partner_earnings.dart';
import 'package:pest_99_partner_app/models/partner_profile.dart';

void main() {
  group('PartnerEarning / EarningsHistory', () {
    test('parses earnings payload with settlement fields', () {
      final history = EarningsHistory.fromJson({
        'total_earnings': '1200.00',
        'approved_earnings': '800.00',
        'results': [
          {
            'id': 1,
            'job_code': 'JC-1',
            'service_type': 'General Pest',
            'amount': '400.00',
            'earning_type': 'revenue_share',
            'is_approved': true,
            'payout_status': 'pending',
            'visit_payout_amount': '400.00',
            'settlement_status': null,
            'settlement_id': null,
            'completed_at': '2026-07-01T10:00:00Z',
            'created_at': '2026-07-01T10:05:00Z',
          },
        ],
      });

      expect(history.totalEarnings, '1200.00');
      expect(history.approvedEarnings, '800.00');
      expect(history.results, hasLength(1));
      expect(history.results.first.amount, '400.00');
      expect(history.results.first.isApproved, isTrue);
      expect(history.results.first.payoutStatus, 'pending');
    });
  });

  group('PartnerPresence', () {
    test('parses suspended status', () {
      final p = PartnerPresence.fromJson({
        'presence_status': 'suspended',
        'presence_label': 'Suspended',
        'last_active': null,
        'is_available': false,
        'is_suspended': true,
        'is_on_leave': false,
        'unavailable_reason': 'Your account is suspended. Docs pending',
        'suspend_reason': 'Docs pending',
        'technician_linked': true,
        'technician_type': 'partner',
      });
      expect(p.isSuspended, isTrue);
      expect(p.suspendReason, 'Docs pending');
      expect(p.isActive, isFalse);
      expect(p.isUnavailable, isTrue);
      expect(p.displayLabel, 'Suspended');
    });

    test('parses on-leave status', () {
      final p = PartnerPresence.fromJson({
        'presence_status': 'on_leave',
        'presence_label': 'On Leave',
        'is_available': false,
        'is_suspended': false,
        'is_on_leave': true,
        'unavailable_reason': 'You are marked as on leave. Contact CRM admin.',
        'technician_linked': true,
      });
      expect(p.isOnLeave, isTrue);
      expect(p.isSuspended, isFalse);
      // On leave blocks work exactly like suspension does.
      expect(p.isUnavailable, isTrue);
      expect(p.isActive, isFalse);
      expect(p.displayLabel, 'On Leave');
    });

    test('parses active status', () {
      final p = PartnerPresence.fromJson({
        'presence_status': 'active',
        'presence_label': 'Active',
        'is_available': true,
        'is_suspended': false,
        'is_on_leave': false,
        'unavailable_reason': '',
        'technician_linked': true,
      });
      expect(p.isActive, isTrue);
      expect(p.isAvailable, isTrue);
      expect(p.isUnavailable, isFalse);
    });

    test('labels a status the server sent without a label', () {
      final p = PartnerPresence.fromJson({'presence_status': 'on_leave'});
      // is_on_leave was absent, so it has to be derived from the status.
      expect(p.isOnLeave, isTrue);
      expect(p.isAvailable, isFalse);
      expect(p.displayLabel, 'On Leave');
    });
  });

  group('PartnerProfile presence', () {
    test('fromJson reads nested presence', () {
      final profile = PartnerProfile.fromJson({
        'id': 9,
        'full_name': 'Tech',
        'mobile': '9999999999',
        'role': 'technician',
        'is_active': true,
        'is_app_approved': true,
        'presence': {
          'presence_status': 'active',
          'presence_label': 'Active',
          'is_available': true,
          'is_suspended': false,
          'is_on_leave': false,
          'suspend_reason': '',
          'technician_linked': true,
        },
      });
      expect(profile.presence?.isActive, isTrue);
      expect(profile.isSuspended, isFalse);
      expect(profile.isUnavailable, isFalse);
      expect(profile.statusLabel, 'Active');
    });

    test('surfaces an on-leave technician as unavailable', () {
      final profile = PartnerProfile.fromJson({
        'id': 10,
        'full_name': 'Tech',
        'mobile': '9999999998',
        'role': 'technician',
        'is_active': true,
        'is_app_approved': true,
        'presence': {
          'presence_status': 'on_leave',
          'presence_label': 'On Leave',
          'is_available': false,
          'is_on_leave': true,
          'technician_linked': true,
        },
      });
      expect(profile.isOnLeave, isTrue);
      expect(profile.isUnavailable, isTrue);
      expect(profile.statusLabel, 'On Leave');
    });
  });

  group('PartnerBooking payout fields', () {
    test('fromJson and hasRevenuePayout', () {
      final booking = PartnerBooking.fromJson({
        'id': 3,
        'service_type': 'General Pest',
        'partner_status': 'completed',
        'price': '1000',
        'payment_model': 'revenue_sharing',
        'visit_payout_amount': '400.00',
        'payout_status': 'pending',
      });
      expect(booking.visitPayoutAmount, '400.00');
      expect(booking.hasRevenuePayout, isTrue);
    });

    test('legacy booking without payout', () {
      final booking = PartnerBooking.fromJson({
        'id': 4,
        'service_type': 'General Pest',
        'partner_status': 'completed',
        'price': '1000',
        'payout_status': 'legacy_exempt',
      });
      expect(booking.hasRevenuePayout, isFalse);
    });

    test('parses completed_at from list payload', () {
      final booking = PartnerBooking.fromJson({
        'id': 469,
        'service_type': 'Cockroach / Ants',
        'partner_status': 'completed',
        'client_name': 'Adnan Shaikh',
        'payment_status': 'Paid',
        'completed_at': '2026-05-27T14:30:00Z',
        'visit_payout_amount': '0.00',
        'payout_status': 'legacy_exempt',
      });
      expect(booking.completedAt, '2026-05-27T14:30:00Z');
      expect(booking.clientName, 'Adnan Shaikh');
      expect(booking.hasRevenuePayout, isFalse);
    });
  });

  group('PartnerLeaveRequest', () {
    test('parses pending leave', () {
      final leave = PartnerLeaveRequest.fromJson({
        'id': 2,
        'start_date': '2026-08-01',
        'end_date': '2026-08-03',
        'reason': 'Family',
        'status': 'pending',
        'admin_note': '',
      });
      expect(leave.isPending, isTrue);
      expect(leave.startDate, '2026-08-01');
    });
  });
}
