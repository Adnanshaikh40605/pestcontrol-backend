import 'dart:async';

import 'package:flutter/foundation.dart';

import 'debug_config.dart';
import 'debug_log_store.dart';
import 'debug_network_service.dart';

/// Installs global error handlers and network monitor (debug only).
class DebugBootstrap {
  DebugBootstrap._();

  static void run(void Function() appRunner) {
    if (!DebugConfig.enabled) {
      appRunner();
      return;
    }

    DebugNetworkService.instance.start();

    final defaultOnError = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      DebugLogStore.instance.logFlutterError(details);
      defaultOnError?.call(details);
    };

    final platformOnError = PlatformDispatcher.instance.onError;
    PlatformDispatcher.instance.onError = (error, stack) {
      DebugLogStore.instance.logZoneError(error, stack);
      return platformOnError?.call(error, stack) ?? false;
    };

    runZonedGuarded(
      appRunner,
      (error, stack) {
        DebugLogStore.instance.logZoneError(error, stack);
        if (kDebugMode) {
          FlutterError.dumpErrorToConsole(
            FlutterErrorDetails(exception: error, stack: stack),
          );
        }
      },
    );
  }
}
