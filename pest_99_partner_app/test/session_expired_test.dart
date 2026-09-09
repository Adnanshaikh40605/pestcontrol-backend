import 'package:flutter_test/flutter_test.dart';

import 'package:pest_99_partner_app/core/api_exception.dart';

void main() {
  group('isPartnerSessionExpiredError', () {
    test('detects 401 status', () {
      expect(
        isPartnerSessionExpiredError(ApiException('x', statusCode: 401)),
        isTrue,
      );
    });

    test('detects backend partner session copy', () {
      expect(
        isPartnerSessionExpiredError(
          ApiException(
            'Invalid or expired partner session. Please log in again.',
            statusCode: 403,
          ),
        ),
        isTrue,
      );
    });

    test('ignores unrelated errors', () {
      expect(
        isPartnerSessionExpiredError(
          ApiException('Could not load bookings.', statusCode: 500),
        ),
        isFalse,
      );
    });
  });
}
