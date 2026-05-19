import 'package:flutter/foundation.dart';

/// Debug tools are active only in debug/developer builds — never in release.
class DebugConfig {
  DebugConfig._();

  static bool get enabled => kDebugMode && !kReleaseMode;
}
