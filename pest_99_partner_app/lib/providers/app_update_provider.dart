import 'package:flutter/foundation.dart';

import '../core/models/app_version_info.dart';
import '../services/app_version_service.dart';

enum AppUpdateCheckStatus {
  idle,
  checking,
  upToDate,
  forceUpdateRequired,
  checkFailed,
}

class AppUpdateProvider extends ChangeNotifier {
  AppUpdateProvider(this._service);

  final AppVersionService _service;

  AppUpdateCheckStatus status = AppUpdateCheckStatus.idle;
  String currentVersion = '';
  AppVersionInfo? serverInfo;
  String? checkError;

  /// Once true from a successful policy response, stays true until a later
  /// successful response says the install is allowed again. Network failures
  /// must not unlock a blocked technician.
  bool _forceUpdateRequired = false;
  bool _checking = false;

  bool get isChecking => _checking;
  bool get forceUpdateRequired => _forceUpdateRequired;

  /// [silent] — background check (app resume) without flipping UI to "checking".
  Future<void> checkForUpdate({bool silent = false}) async {
    if (!silent) {
      _checking = true;
      checkError = null;
      status = AppUpdateCheckStatus.checking;
      notifyListeners();
    }

    try {
      final result = await _service.fetchVersionPolicy();
      currentVersion = result.currentVersion;
      serverInfo = result.server;

      final blocked = _service.requiresForceUpdate(
        currentVersion: currentVersion,
        server: result.server,
      );

      _forceUpdateRequired = blocked;
      status = blocked
          ? AppUpdateCheckStatus.forceUpdateRequired
          : AppUpdateCheckStatus.upToDate;
      checkError = null;
    } catch (e) {
      debugPrint('[AppUpdate] version check failed: $e');
      checkError = e.toString();
      // Fail open only when we have never confirmed a block.
      // If already blocked, keep the gate locked through API outages.
      if (!_forceUpdateRequired) {
        status = AppUpdateCheckStatus.checkFailed;
      }
    } finally {
      _checking = false;
      notifyListeners();
    }
  }
}
