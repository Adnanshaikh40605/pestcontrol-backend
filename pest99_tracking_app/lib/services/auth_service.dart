import '../config/api_config.dart';
import '../core/api_client.dart';
import '../core/api_exception.dart';

class AuthService {
  AuthService(this._api);
  final ApiClient _api;

  static String normalizeMobile(String mobile) {
    final digits = mobile.replaceAll(RegExp(r'\D'), '');
    if (digits.length > 10) return digits.substring(digits.length - 10);
    return digits;
  }

  Future<Map<String, dynamic>> login(String mobile, String password) async {
    final data = await _api.post(
      ApiConfig.login,
      body: {
        'mobile': normalizeMobile(mobile),
        'password': password,
      },
      auth: false,
    );
    final access = data['access'] as String?;
    final refresh = data['refresh'] as String?;
    final authType = (data['auth_type'] as String?) ?? 'partner';
    if (access == null || refresh == null) {
      throw ApiException('Login failed — no token received.');
    }
    await _api.saveSessionTokens(access: access, refresh: refresh, authType: authType);
    return data;
  }

  Future<void> logout() => _api.clearSession();
  Future<bool> hasSession() => _api.hasSession();
}
