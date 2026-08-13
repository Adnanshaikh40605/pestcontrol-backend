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
    test('parses suspended presence', () {
      final p = PartnerPresence.fromJson({
        'presence_status': 'suspended',
        'last_active': null,
        'is_suspended': true,
        'suspend_reason': 'Docs pending',
        'technician_linked': true,
        'technician_type': 'partner',
      });
      expect(p.isSuspended, isTrue);
      expect(p.suspendReason, 'Docs pending');
      expect(p.isOnline, isFalse);
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
          'presence_status': 'online',
          'is_suspended': false,
          'suspend_reason': '',
          'technician_linked': true,
        },
      });
      expect(profile.presence?.isOnline, isTrue);
      expect(profile.isSuspended, isFalse);
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
