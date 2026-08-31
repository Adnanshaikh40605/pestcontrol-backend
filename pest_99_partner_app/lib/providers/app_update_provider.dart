import 'package:flutter/foundation.dart';

import '../core/models/app_version_info.dart';
import '../services/app_version_service.dart';

enum AppUpdateCheckStatus {
  idle,
  checking,
  upToDate,
  forceUpdateRequired,
  updateAvailable,
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
  /// successful response says the install is allowed again.
  bool _forceUpdateRequired = false;
  bool _updateAvailable = false;
  bool _checking = false;

  bool get isChecking => _checking;
  bool get forceUpdateRequired => _forceUpdateRequired;
  bool get updateAvailable => _updateAvailable;

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

      final behind = _service.isUpdateAvailable(
        currentVersion: currentVersion,
        server: result.server,
      );
      final blocked = _service.requiresForceUpdate(
        currentVersion: currentVersion,
        server: result.server,
      );

      _forceUpdateRequired = blocked;
      _updateAvailable = behind;
      status = blocked
          ? AppUpdateCheckStatus.forceUpdateRequired
          : behind
              ? AppUpdateCheckStatus.updateAvailable
              : AppUpdateCheckStatus.upToDate;
      checkError = null;
    } catch (e) {
      debugPrint('[AppUpdate] version check failed: $e');
      checkError = e.toString();
      if (!_forceUpdateRequired) {
        status = AppUpdateCheckStatus.checkFailed;
      }
    } finally {
      _checking = false;
      notifyListeners();
    }
  }
}
