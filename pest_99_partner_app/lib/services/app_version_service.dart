import 'package:package_info_plus/package_info_plus.dart';

import '../config/api_config.dart';
import '../core/api_client.dart';
import '../core/models/app_version_info.dart';
import '../core/utils/version_utils.dart';

class AppVersionService {
  AppVersionService(this._api);

  final ApiClient _api;

  Future<({String currentVersion, AppVersionInfo server})> fetchVersionPolicy() async {
    final packageInfo = await PackageInfo.fromPlatform();
    final currentVersion = normalizeVersion(packageInfo.version);

    final data = await _api.get(ApiConfig.appVersion, auth: false);
    final server = AppVersionInfo.fromJson(data);

    return (currentVersion: currentVersion, server: server);
  }

  bool requiresForceUpdate({
    required String currentVersion,
    required AppVersionInfo server,
  }) {
    if (!server.forceUpdate) return false;
    // Block when below the configured minimum OR below the published latest.
    // Admin typically sets both to the current Play Store version when forcing.
    if (isVersionBelow(currentVersion, server.minimumSupportedVersion)) {
      return true;
    }
    return isVersionBelow(currentVersion, server.latestVersion);
  }

  /// True when the installed app is older than the published Play Store version.
  bool isUpdateAvailable({
    required String currentVersion,
    required AppVersionInfo server,
  }) {
    return isVersionBelow(currentVersion, server.latestVersion);
  }
}
