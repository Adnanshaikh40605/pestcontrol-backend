import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureTokenStorage {
  SecureTokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  static const _accessKey = 'tracking_access_token';
  static const _refreshKey = 'tracking_refresh_token';
  static const _authTypeKey = 'tracking_auth_type';

  final FlutterSecureStorage _storage;

  Future<void> saveTokens({
    required String access,
    required String refresh,
    required String authType,
  }) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
    await _storage.write(key: _authTypeKey, value: authType);
  }

  Future<String?> getAccessToken() => _storage.read(key: _accessKey);
  Future<String?> getRefreshToken() => _storage.read(key: _refreshKey);
  Future<String?> getAuthType() => _storage.read(key: _authTypeKey);

  Future<bool> hasSession() async {
    final access = await getAccessToken();
    return access != null && access.isNotEmpty;
  }

  Future<void> clearAll() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _authTypeKey);
  }
}
