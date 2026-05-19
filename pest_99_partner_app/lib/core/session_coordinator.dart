import 'package:flutter/foundation.dart';

/// Global session-expired signal (e.g. after 60-day refresh expiry).
class SessionCoordinator extends ChangeNotifier {
  String? _message;

  String? get sessionExpiredMessage => _message;

  void notifySessionExpired([String message = 'Session expired. Please login again.']) {
    _message = message;
    notifyListeners();
  }

  void clearMessage() {
    _message = null;
  }
}
