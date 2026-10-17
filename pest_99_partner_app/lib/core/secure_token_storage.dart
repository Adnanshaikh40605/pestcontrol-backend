import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Encrypted storage for JWT access + refresh tokens.
///
/// On web, [FlutterSecureStorage] uses Web Crypto + localStorage and can throw
/// [TypeError] (null-check / crypto failures). Prefer SharedPreferences
/// (browser localStorage) so login works in Chrome local previews.
class SecureTokenStorage {
  SecureTokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  static const _accessKey = 'partner_access_token';
  static const _refreshKey = 'partner_refresh_token';
  static const _legacyAccessKey = 'partner_access_token';

  final FlutterSecureStorage _storage;
  bool _migrated = false;

  bool get _usePrefs => kIsWeb;

  Future<void> _migrateFromSharedPreferencesIfNeeded() async {
    if (_migrated || _usePrefs) return;
    _migrated = true;

    final existingAccess = await _storage.read(key: _accessKey);
    if (existingAccess != null && existingAccess.isNotEmpty) return;

    final prefs = await SharedPreferences.getInstance();
    final legacyAccess = prefs.getString(_legacyAccessKey);
    if (legacyAccess != null && legacyAccess.isNotEmpty) {
      await _storage.write(key: _accessKey, value: legacyAccess);
      await prefs.remove(_legacyAccessKey);
    }
  }

  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    if (_usePrefs) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_accessKey, access);
      await prefs.setString(_refreshKey, refresh);
      return;
    }
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<String?> getAccessToken() async {
    if (_usePrefs) {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(_accessKey);
    }
    await _migrateFromSharedPreferencesIfNeeded();
    return _storage.read(key: _accessKey);
  }

  Future<String?> getRefreshToken() async {
    if (_usePrefs) {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(_refreshKey);
    }
    await _migrateFromSharedPreferencesIfNeeded();
    return _storage.read(key: _refreshKey);
  }

  Future<bool> hasSession() async {
    final access = await getAccessToken();
    return access != null && access.isNotEmpty;
  }

  Future<void> clearAll() async {
    if (_usePrefs) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_accessKey);
      await prefs.remove(_refreshKey);
      return;
    }
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_legacyAccessKey);
  }
}
