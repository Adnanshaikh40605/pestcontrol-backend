import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../core/api_exception.dart';
import '../models/customer_models.dart';
import '../services/customer_services.dart';

class OtpSendResult {
  const OtpSendResult({required this.ok, this.devOtp, this.error});

  final bool ok;
  final String? devOtp;
  final String? error;
}

class OtpVerifyResult {
  const OtpVerifyResult({
    required this.ok,
    this.error,
    this.code,
    this.mobile,
    this.action,
  });

  final bool ok;
  final String? error;
  final String? code;
  final String? mobile;
  final String? action;

  bool get needsRegistration => code == 'not_registered' || action == 'register';
}

class AuthProvider extends ChangeNotifier {
  AuthProvider(this._api) : _auth = AuthService(_api);

  final ApiClient _api;
  final AuthService _auth;

  CustomerProfile? profile;
  bool ready = false;
  bool loggedIn = false;
  String? error;

  /// After login, navigate here (e.g. '/book/property').
  String? pendingRoute;

  void setPendingRoute(String? route) {
    pendingRoute = route;
  }

  String? takePendingRoute() {
    final route = pendingRoute;
    pendingRoute = null;
    return route;
  }

  Future<void> bootstrap() async {
    loggedIn = await _api.hasSession();
    if (loggedIn) {
      try {
        profile = await _auth.getProfile();
      } catch (_) {
        loggedIn = false;
        await _api.clearTokens();
      }
    }
    ready = true;
    notifyListeners();
  }

  Future<OtpSendResult> sendOtp({
    required String mobile,
    required String purpose,
    String fullName = '',
  }) async {
    error = null;
    try {
      final data = await _auth.sendOtp(mobile: mobile, purpose: purpose, fullName: fullName);
      // Only surface OTP in debug builds — never in release/Play builds.
      final dev = kDebugMode ? data['dev_otp']?.toString() : null;
      notifyListeners();
      return OtpSendResult(ok: true, devOtp: dev);
    } catch (e) {
      error = '$e';
      notifyListeners();
      return OtpSendResult(ok: false, error: error);
    }
  }

  Future<OtpVerifyResult> verifyOtp({
    required String mobile,
    required String otp,
    required String purpose,
    String fullName = '',
  }) async {
    error = null;
    try {
      profile = await _auth.verifyOtp(
        mobile: mobile,
        otp: otp,
        purpose: purpose,
        fullName: fullName,
      );
      loggedIn = true;
      notifyListeners();
      return const OtpVerifyResult(ok: true);
    } catch (e) {
      error = '$e';
      notifyListeners();
      if (e is ApiException) {
        return OtpVerifyResult(
          ok: false,
          error: e.message,
          code: e.code,
          mobile: mobile,
          action: e.code == 'not_registered' ? 'register' : null,
        );
      }
      return OtpVerifyResult(ok: false, error: error, mobile: mobile);
    }
  }

  Future<bool> updateProfile({required String fullName}) async {
    error = null;
    try {
      profile = await _auth.updateProfile(fullName: fullName);
      notifyListeners();
      return true;
    } catch (e) {
      error = '$e';
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteAccount() async {
    error = null;
    try {
      await _auth.deleteAccount();
      profile = null;
      loggedIn = false;
      pendingRoute = null;
      notifyListeners();
      return true;
    } catch (e) {
      error = '$e';
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _auth.logout();
    profile = null;
    loggedIn = false;
    pendingRoute = null;
    notifyListeners();
  }
}
