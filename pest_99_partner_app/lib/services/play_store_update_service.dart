import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:in_app_update/in_app_update.dart';

/// Checks Google Play for a newer release and shows the native Play update UI.
///
/// Works only for Play Store installs. Sideloaded / debug / emulator builds
/// fail silently so development is never blocked.
class PlayStoreUpdateService {
  PlayStoreUpdateService._();

  static Future<void> checkAndPromptUpdate() async {
    if (kIsWeb || !Platform.isAndroid) return;

    try {
      final info = await InAppUpdate.checkForUpdate();
      if (info.updateAvailability != UpdateAvailability.updateAvailable) {
        return;
      }

      // Immediate update = native Play "Update available" dialog (user screenshot).
      if (info.immediateUpdateAllowed) {
        await InAppUpdate.performImmediateUpdate();
        return;
      }

      // Fallback when immediate is not offered by Play for this release.
      if (info.flexibleUpdateAllowed) {
        final result = await InAppUpdate.startFlexibleUpdate();
        if (result == AppUpdateResult.success) {
          await InAppUpdate.completeFlexibleUpdate();
        }
      }
    } catch (e, st) {
      debugPrint('[PlayUpdate] check skipped: $e\n$st');
    }
  }
}
