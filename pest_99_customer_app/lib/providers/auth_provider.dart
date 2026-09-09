import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../core/api_exception.dart';
import '../models/customer_models.dart';
import '../services/customer_services.dart';

class OtpSendResult {
  const OtpSendResult({required this.ok, this.devOtp, this.error, this.code});

  final bool ok;
  final String? devOtp;
  final String? error;
  final String? code;

  bool get alreadyRegistered {
    if (code == 'already_registered') return true;
    final lower = (error ?? '').toLowerCase();
    return lower.contains('already exists') ||
        lower.contains('already registered') ||
        lower.contains('please login');
  }

  bool get needsRegistration {
    if (code == 'not_registered') return true;
    final lower = (error ?? '').toLowerCase();
    return lower.contains('not registered') ||
        lower.contains('isn\'t registered') ||
        lower.contains('register to continue') ||
        lower.contains('create your account');
  }
}

/// Result of Login "Continue" — lookup then optional login OTP send.
class LoginContinueResult {
  const LoginContinueResult({
    required this.ok,
    required this.registered,
    this.devOtp,
    this.error,
    this.code,
  });

  final bool ok;
  final bool registered;
  final String? devOtp;
  final String? error;
  final String? code;

  bool get needsRegistration => !registered || code == 'not_registered';
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

  /// After login/register OTP, navigate here (e.g. '/book/property').
  String? pendingRoute;

  /// Kept across Register → OTP so name is never lost if route extras drop.
  String? pendingRegisterName;
  String? pendingRegisterMobile;

  void setPendingRoute(String? route) {
    pendingRoute = route;
  }

  String? takePendingRoute() {
    final route = pendingRoute;
    pendingRoute = null;
    return route;
  }

  void setRegistrationDraft({required String fullName, required String mobile}) {
    pendingRegisterName = fullName.trim();
    pendingRegisterMobile = mobile.trim();
  }

  void clearRegistrationDraft() {
    pendingRegisterName = null;
    pendingRegisterMobile = null;
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
    if (purpose == 'register') {
      setRegistrationDraft(fullName: fullName, mobile: mobile);
    }
    try {
      final data = await _auth.sendOtp(mobile: mobile, purpose: purpose, fullName: fullName);
      // Only surface OTP in debug builds — never in release/Play builds.
      final dev = kDebugMode ? data['dev_otp']?.toString() : null;
      notifyListeners();
      return OtpSendResult(ok: true, devOtp: dev);
    } catch (e) {
      if (e is ApiException &&
          (e.code == 'already_registered' || e.code == 'not_registered')) {
        // Expected business state — not a sticky form error.
        error = null;
        notifyListeners();
        return OtpSendResult(ok: false, error: e.message, code: e.code);
      }
      error = '$e';
      notifyListeners();
      final code = e is ApiException ? e.code : null;
      return OtpSendResult(ok: false, error: error, code: code);
    }
  }

  /// Login entry: lookup mobile first, then send login OTP only if registered.
  Future<LoginContinueResult> continueWithMobile(String mobile) async {
    error = null;
    try {
      final lookup = await _auth.lookupMobile(mobile);
      final registered = lookup['registered'] == true;
      if (!registered) {
        notifyListeners();
        return const LoginContinueResult(
          ok: true,
          registered: false,
          code: 'not_registered',
        );
      }
      final otp = await sendOtp(mobile: mobile, purpose: 'login');
      if (!otp.ok) {
        return LoginContinueResult(
          ok: false,
          registered: true,
          error: otp.error,
          code: otp.code,
        );
      }
      return LoginContinueResult(
        ok: true,
        registered: true,
        devOtp: otp.devOtp,
      );
    } catch (e) {
      error = '$e';
      notifyListeners();
      return LoginContinueResult(
        ok: false,
        registered: false,
        error: error,
        code: e is ApiException ? e.code : null,
      );
    }
  }

  Future<OtpVerifyResult> verifyOtp({
    required String mobile,
    required String otp,
    required String purpose,
    String fullName = '',
  }) async {
    error = null;
    final name = fullName.trim().isNotEmpty
        ? fullName.trim()
        : (pendingRegisterName ?? '');
    try {
      profile = await _auth.verifyOtp(
        mobile: mobile,
        otp: otp,
        purpose: purpose,
        fullName: name,
      );
      loggedIn = true;
      clearRegistrationDraft();
      // If profile payload was incomplete, refresh from API while session is live.
      if (profile == null || profile!.id <= 0 || profile!.fullName.trim().isEmpty) {
        try {
          profile = await _auth.getProfile();
        } catch (_) {
          // Session tokens are already saved; Home can still load.
        }
      }
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
          action: e.action ?? (e.code == 'not_registered' ? 'register' : null),
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
      clearRegistrationDraft();
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
    clearRegistrationDraft();
    notifyListeners();
  }
}
