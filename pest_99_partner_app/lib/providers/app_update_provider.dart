import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/models/app_version_info.dart';
import '../services/app_version_service.dart';

const _versionCheckTimeout = Duration(seconds: 8);

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

  bool get isChecking => status == AppUpdateCheckStatus.checking;
  bool get forceUpdateRequired =>
      status == AppUpdateCheckStatus.forceUpdateRequired;

  /// [silent] — background check (app resume) without redirecting to splash.
  Future<void> checkForUpdate({bool silent = false}) async {
    if (!silent) {
      status = AppUpdateCheckStatus.checking;
      checkError = null;
      notifyListeners();
    }

    try {
      final result = await _service
          .fetchVersionPolicy()
          .timeout(_versionCheckTimeout);
      currentVersion = result.currentVersion;
      serverInfo = result.server;

      final blocked = _service.requiresForceUpdate(
        currentVersion: currentVersion,
        server: result.server,
      );

      status = blocked
          ? AppUpdateCheckStatus.forceUpdateRequired
          : AppUpdateCheckStatus.upToDate;
    } on TimeoutException {
      debugPrint('[AppUpdate] version check timed out');
      checkError = 'Version check timed out';
      status = AppUpdateCheckStatus.checkFailed;
    } catch (e) {
      debugPrint('[AppUpdate] version check failed: $e');
      checkError = e.toString();
      status = AppUpdateCheckStatus.checkFailed;
    }
    notifyListeners();
  }
}
