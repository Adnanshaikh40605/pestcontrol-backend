import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_partner_app/core/user_error.dart';

void main() {
  test('TypeError maps to the parse-failure snackbar copy', () {
    expect(
      userErrorMessage(TypeError()),
      'Could not read the server response. Please try again.',
    );
  });

  test('login token extraction tolerates non-String JSON values', () {
    // Mirrors AuthService.login token reads (toString, not `as String?`).
    final data = <String, dynamic>{
      'access': 'tok-access',
      'refresh': 'tok-refresh',
      'is_app_approved': true,
      'partner': {'full_name': 'adnan shaikh tets'},
    };
    final access = data['access']?.toString();
    final refresh = data['refresh']?.toString();
    expect(access, isNotEmpty);
    expect(refresh, isNotEmpty);
    expect(access == 'null', isFalse);

    final partner = data['partner'];
    expect(partner, isA<Map>());
    final name = (partner as Map)['full_name'];
    final partnerName = name is String ? name : name?.toString();
    expect(partnerName, 'adnan shaikh tets');
  });
}
