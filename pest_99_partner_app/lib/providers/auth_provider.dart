import 'package:flutter/foundation.dart';

import '../core/api_exception.dart';
import '../core/session_coordinator.dart';
import '../services/auth_service.dart';
import '../services/push_notification_service.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider(this._auth, this._session) {
    _session.addListener(_onSessionEvent);
  }

  final AuthService _auth;
  final SessionCoordinator _session;

  bool _loading = false;
  String? _error;
  bool _loggedIn = false;
  bool _appApproved = false;
  bool _ready = false;
  String? _partnerName;
  String? _sessionExpiredMessage;

  bool get loading => _loading;
  String? get error => _error;
  bool get loggedIn => _loggedIn;
  bool get appApproved => _appApproved;
  bool get ready => _ready;
  String? get partnerName => _partnerName;
  String? get sessionExpiredMessage => _sessionExpiredMessage;

  void _onSessionEvent() {
    final msg = _session.sessionExpiredMessage;
    if (msg != null && _loggedIn) {
      _sessionExpiredMessage = msg;
      _loggedIn = false;
      _appApproved = false;
      _partnerName = null;
      notifyListeners();
    }
  }

  Future<void> init() async {
    _loggedIn = await _auth.hasSession();
    _appApproved = _loggedIn ? await _auth.isAppApproved() : false;
    if (_loggedIn) {
      await _setupPushAfterAuth();
    }
    _ready = true;
    notifyListeners();
  }

  Future<void> _setupPushAfterAuth() async {
    await PushNotificationService.instance.requestPermission();
    await PushNotificationService.instance.getToken();
    await PushNotificationService.instance.syncTokenWithBackend();
  }

  void clearSessionMessage() {
    _sessionExpiredMessage = null;
    _session.clearMessage();
  }

  Future<bool> login(String mobile, String password) async {
    _loading = true;
    _error = null;
    _sessionExpiredMessage = null;
    _session.clearMessage();
    notifyListeners();
    try {
      final data = await _auth.login(mobile, password);
      _loggedIn = true;
      _appApproved = data['is_app_approved'] == true;
      final partner = data['partner'];
      if (partner is Map) {
        _partnerName = partner['full_name'] as String?;
      }
      await PushNotificationService.instance.requestPermission();
      await PushNotificationService.instance.getToken();
      try {
        await PushNotificationService.instance.syncTokenWithBackend();
      } catch (e) {
        debugPrint('FCM token sync after login failed: $e');
      }
      await PushNotificationService.instance.showLoginSuccessNotification();
      return true;
    } on ApiException catch (e) {
      _error = e.message;
      return false;
    } catch (_) {
      _error = 'Network error. Check your connection.';
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<bool> register({
    required String fullName,
    required String mobile,
    required String password,
  }) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      await _auth.register(fullName: fullName, mobile: mobile, password: password);
      return true;
    } on ApiException catch (e) {
      _error = e.message;
      return false;
    } catch (_) {
      _error = 'Registration failed. Check your connection.';
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> refreshApprovalFromProfile(Map<String, dynamic> data) async {
    _appApproved = data['is_app_approved'] == true;
    await _auth.setAppApproved(_appApproved);
    final partner = data['partner'];
    if (partner is Map) {
      _partnerName = partner['full_name'] as String?;
    }
    if (_loggedIn) {
      await PushNotificationService.instance.syncTokenWithBackend();
    }
    notifyListeners();
  }

  Future<void> logout() async {
    await PushNotificationService.instance.removeTokenFromBackend();
    await _auth.logout();
    _loggedIn = false;
    _appApproved = false;
    _partnerName = null;
    _session.clearMessage();
    notifyListeners();
  }

  @override
  void dispose() {
    _session.removeListener(_onSessionEvent);
    super.dispose();
  }
}
