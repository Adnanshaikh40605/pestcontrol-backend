import 'package:shared_preferences/shared_preferences.dart';

import '../config/api_config.dart';
import '../core/api_client.dart';
import '../core/api_exception.dart';

class AuthService {
  AuthService(this._api);

  final ApiClient _api;
  static const _approvedKey = 'partner_app_approved';

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
    // Use toString() — web JSON maps can yield non-Dart-String values that
    // fail a hard `as String?` cast (TypeError → misleading parse error UI).
    final access = data['access']?.toString();
    final refresh = data['refresh']?.toString();
    if (access == null || access.isEmpty || access == 'null') {
      throw ApiException('Login failed — no token received.');
    }
    if (refresh == null || refresh.isEmpty || refresh == 'null') {
      throw ApiException('Login failed — no refresh token received.');
    }
    await _api.saveSessionTokens(access: access, refresh: refresh);
    final approved = data['is_app_approved'] == true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_approvedKey, approved);
    return data;
  }

  Future<void> register({
    required String fullName,
    required String mobile,
    required String password,
    String role = 'technician',
  }) async {
    await _api.post(
      ApiConfig.register,
      body: {
        'full_name': fullName,
        'mobile': normalizeMobile(mobile),
        'password': password,
        'role': role,
      },
      auth: false,
    );
  }

  Future<Map<String, dynamic>> sendPasswordOtp(String mobile) {
    return _api.post(
      ApiConfig.passwordOtp,
      body: {'mobile': normalizeMobile(mobile)},
      auth: false,
    );
  }

  Future<void> resetPassword({
    required String mobile,
    required String otp,
    required String newPassword,
  }) async {
    await _api.post(
      ApiConfig.passwordReset,
      body: {
        'mobile': normalizeMobile(mobile),
        'otp': otp.replaceAll(RegExp(r'\D'), ''),
        'new_password': newPassword,
      },
      auth: false,
    );
  }

  Future<bool> isAppApproved() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_approvedKey) ?? false;
  }

  Future<void> setAppApproved(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_approvedKey, value);
  }

  Future<void> logout() async {
    await _api.clearSession();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_approvedKey);
  }

  Future<bool> hasSession() => _api.hasSession();

  Future<void> deleteAccount({required String password}) async {
    await _api.delete(
      ApiConfig.deleteAccount,
      body: {
        'password': password,
        'confirm': true,
      },
    );
    await logout();
  }
}
