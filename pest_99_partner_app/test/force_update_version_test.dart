import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_partner_app/core/api_client.dart';
import 'package:pest_99_partner_app/core/models/app_version_info.dart';
import 'package:pest_99_partner_app/core/utils/version_utils.dart';
import 'package:pest_99_partner_app/providers/app_update_provider.dart';
import 'package:pest_99_partner_app/services/app_version_service.dart';

bool requiresForceUpdate({
  required String currentVersion,
  required AppVersionInfo server,
}) {
  if (!server.forceUpdate) return false;
  return isVersionBelow(currentVersion, server.minimumSupportedVersion);
}

class _FakeVersionService extends AppVersionService {
  _FakeVersionService()
      : super(
          ApiClient(
            dio: Dio(BaseOptions(baseUrl: 'http://127.0.0.1')),
          ),
        );

  AppVersionInfo? nextServer;
  Object? nextError;

  @override
  Future<({String currentVersion, AppVersionInfo server})> fetchVersionPolicy() async {
    if (nextError != null) throw nextError!;
    return (currentVersion: '2.0.7', server: nextServer!);
  }
}

void main() {
  group('version_utils', () {
    test('compare and normalize', () {
      expect(compareVersions('2.0.7', '2.0.8'), -1);
      expect(compareVersions('2.0.8', '2.0.8'), 0);
      expect(compareVersions('2.1.0', '2.0.8'), 1);
      expect(isVersionBelow('2.0.7+9', '2.0.8'), isTrue);
      expect(isVersionBelow('2.0.8+10', '2.0.8'), isFalse);
      expect(normalizeVersion('2.0.8+10'), '2.0.8');
    });
  });

  group('force update policy', () {
    AppVersionInfo policy({required bool force, required String min}) {
      return AppVersionInfo(
        latestVersion: min,
        minimumSupportedVersion: min,
        forceUpdate: force,
        updateTitle: 'Please update the app.',
        updateMessage: 'Please update the app.',
        storeUrl: AppVersionInfo.defaultStoreUrl,
      );
    }

    test('blocks only when force_update and below minimum', () {
      expect(
        requiresForceUpdate(
          currentVersion: '2.0.7',
          server: policy(force: true, min: '2.0.8'),
        ),
        isTrue,
      );
      expect(
        requiresForceUpdate(
          currentVersion: '2.0.8',
          server: policy(force: true, min: '2.0.8'),
        ),
        isFalse,
      );
      expect(
        requiresForceUpdate(
          currentVersion: '2.0.7',
          server: policy(force: false, min: '2.0.8'),
        ),
        isFalse,
      );
    });

    test('network failure after block does not unlock app', () async {
      final service = _FakeVersionService();
      final provider = AppUpdateProvider(service);

      service.nextServer = policy(force: true, min: '2.0.8');
      await provider.checkForUpdate();
      expect(provider.forceUpdateRequired, isTrue);

      service.nextError = Exception('offline');
      await provider.checkForUpdate(silent: true);
      expect(provider.forceUpdateRequired, isTrue);
      expect(provider.isChecking, isFalse);
    });

    test('successful allow response can unlock after block', () async {
      final service = _FakeVersionService();
      final provider = AppUpdateProvider(service);

      service.nextServer = policy(force: true, min: '2.0.8');
      await provider.checkForUpdate();
      expect(provider.forceUpdateRequired, isTrue);

      service.nextServer = policy(force: false, min: '2.0.8');
      await provider.checkForUpdate(silent: true);
      expect(provider.forceUpdateRequired, isFalse);
    });
  });
}
