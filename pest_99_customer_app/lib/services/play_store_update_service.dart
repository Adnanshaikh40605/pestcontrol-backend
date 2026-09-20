import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:in_app_update/in_app_update.dart';

/// Checks Google Play for a newer release and shows the native Play update UI.
///
/// Works only for Play Store installs. Sideloaded / debug / emulator builds
/// fail silently so development is never blocked.
class PlayStoreUpdateService {
  PlayStoreUpdateService._();

  static const Duration _checkTimeout = Duration(seconds: 8);

  static Future<void> checkAndPromptUpdate() async {
    if (kIsWeb || !Platform.isAndroid) return;

    try {
      final info = await InAppUpdate.checkForUpdate().timeout(_checkTimeout);
      if (info.updateAvailability != UpdateAvailability.updateAvailable) {
        return;
      }

      // Immediate update = native Play "Update available" dialog.
      // Do not await forever — user can dismiss / Play can hang on sideloads.
      if (info.immediateUpdateAllowed) {
        unawaited(
          InAppUpdate.performImmediateUpdate().catchError((Object e, StackTrace st) {
            debugPrint('[PlayUpdate] immediate update failed: $e\n$st');
            return AppUpdateResult.inAppUpdateFailed;
          }),
        );
        return;
      }

      // Fallback when immediate is not offered by Play for this release.
      if (info.flexibleUpdateAllowed) {
        final result = await InAppUpdate.startFlexibleUpdate().timeout(
          const Duration(seconds: 60),
        );
        if (result == AppUpdateResult.success) {
          await InAppUpdate.completeFlexibleUpdate();
        }
      }
    } on TimeoutException catch (e, st) {
      debugPrint('[PlayUpdate] check timed out: $e\n$st');
    } catch (e, st) {
      debugPrint('[PlayUpdate] check skipped: $e\n$st');
    }
  }
}
