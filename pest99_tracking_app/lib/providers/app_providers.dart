import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/session_coordinator.dart';
import '../services/auth_service.dart';
import '../services/location_service.dart';
import '../services/tracking_service.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider(this._auth, this._session) {
    _session.onSessionExpired = () {
      _loggedIn = false;
      notifyListeners();
    };
  }

  final AuthService _auth;
  final SessionCoordinator _session;
  bool _loggedIn = false;
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _profile;

  bool get isLoggedIn => _loggedIn;
  bool get isLoading => _loading;
  String? get error => _error;
  Map<String, dynamic>? get profile => _profile;

  Future<void> init() async {
    _loggedIn = await _auth.hasSession();
    notifyListeners();
  }

  Future<bool> login(String mobile, String password) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      await _auth.login(mobile, password);
      _loggedIn = true;
      return true;
    } catch (e) {
      _error = e.toString();
      _loggedIn = false;
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await _auth.logout();
    _loggedIn = false;
    _profile = null;
    notifyListeners();
  }
}

class TrackingProvider extends ChangeNotifier {
  TrackingProvider(this._tracking, this._location);

  final TrackingService _tracking;
  final LocationService _location;

  Map<String, dynamic>? _me;
  bool _loading = false;
  String? _error;
  StreamSubscription? _gpsSub;
  final List<Map<String, dynamic>> _offlineQueue = [];

  Map<String, dynamic>? get me => _me;
  bool get isLoading => _loading;
  String? get error => _error;
  bool get isCheckedIn => _me?['is_checked_in'] == true;

  Future<void> refreshStatus() async {
    _loading = true;
    notifyListeners();
    try {
      _me = await _tracking.getMe();
      _error = null;
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<bool> acceptConsent() async {
    try {
      await _tracking.recordConsent();
      await refreshStatus();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> checkIn() async {
    try {
      final ok = await _location.ensurePermissions();
      if (!ok) throw Exception('Location permission required.');
      final pos = await _location.getCurrentPosition();
      await _tracking.checkIn(
        latitude: pos.latitude,
        longitude: pos.longitude,
        accuracyM: pos.accuracy,
      );
      await refreshStatus();
      _startGps();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> checkOut() async {
    try {
      final pos = await _location.getCurrentPosition();
      await _tracking.checkOut(
        latitude: pos.latitude,
        longitude: pos.longitude,
        accuracyM: pos.accuracy,
      );
      await _stopGps();
      await _flushQueue();
      await refreshStatus();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  void _startGps() {
    _gpsSub?.cancel();
    final interval = (_me?['settings']?['ping_interval_moving_seconds'] as int?) ?? 30;
    _gpsSub = _location.positionStream(intervalSeconds: interval).listen((pos) async {
      try {
        await _tracking.sendPing(
          latitude: pos.latitude,
          longitude: pos.longitude,
          accuracyM: pos.accuracy,
          isMoving: pos.speed > 0.5,
        );
      } catch (_) {
        _offlineQueue.add({
          'latitude': pos.latitude,
          'longitude': pos.longitude,
          'accuracy_m': pos.accuracy,
          'is_moving': pos.speed > 0.5,
          'recorded_at': DateTime.now().toUtc().toIso8601String(),
        });
      }
    });
  }

  Future<void> _stopGps() async {
    await _gpsSub?.cancel();
    _gpsSub = null;
  }

  Future<void> _flushQueue() async {
    if (_offlineQueue.isEmpty) return;
    final batch = List<Map<String, dynamic>>.from(_offlineQueue);
    _offlineQueue.clear();
    try {
      await _tracking.syncBatch(batch);
    } catch (_) {
      _offlineQueue.insertAll(0, batch);
    }
  }

  @override
  void dispose() {
    _stopGps();
    super.dispose();
  }
}
