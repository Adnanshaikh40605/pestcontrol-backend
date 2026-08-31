import 'package:flutter/foundation.dart';

import '../services/play_store_update_service.dart';

/// Triggers Google Play in-app update checks (no CRM / backend version policy).
class AppUpdateProvider extends ChangeNotifier {
  bool _checking = false;

  bool get isChecking => _checking;

  Future<void> checkForUpdate({bool silent = false}) async {
    if (_checking) return;
    _checking = true;
    if (!silent) notifyListeners();

    try {
      await PlayStoreUpdateService.checkAndPromptUpdate();
    } finally {
      _checking = false;
      notifyListeners();
    }
  }
}
