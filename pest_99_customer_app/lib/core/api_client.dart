import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/api_config.dart';
import 'api_exception.dart';

class ApiClient {
  ApiClient({Dio? dio, FlutterSecureStorage? storage})
      : _dio = dio ?? _createDio(),
        _storage = storage ?? const FlutterSecureStorage();

  final Dio _dio;
  final FlutterSecureStorage _storage;
  static const _accessKey = 'customer_access';
  static const _refreshKey = 'customer_refresh';
  static const Duration _storageTimeout = Duration(seconds: 2);
  static const String offlineMessage =
      'Unable to connect right now. Please check your internet connection and try again.';

  /// On web, [FlutterSecureStorage] uses Web Crypto + localStorage and can
  /// throw [TypeError]. Prefer SharedPreferences (browser localStorage).
  bool get _usePrefs => kIsWeb;

  static Dio _createDio() {
    return Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: const Duration(seconds: 12),
        receiveTimeout: const Duration(seconds: 20),
        headers: {'Accept': 'application/json'},
        validateStatus: (_) => true,
      ),
    );
  }

  Future<void> saveTokens({required String access, required String refresh}) async {
    if (_usePrefs) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_accessKey, access);
      await prefs.setString(_refreshKey, refresh);
      return;
    }
    await _storage.write(key: _accessKey, value: access).timeout(_storageTimeout);
    await _storage.write(key: _refreshKey, value: refresh).timeout(_storageTimeout);
  }

  Future<void> clearTokens() async {
    try {
      if (_usePrefs) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.remove(_accessKey);
        await prefs.remove(_refreshKey);
        return;
      }
      await _storage.delete(key: _accessKey).timeout(_storageTimeout);
      await _storage.delete(key: _refreshKey).timeout(_storageTimeout);
    } catch (_) {
      // Ignore storage hangs / errors on logout path.
    }
  }

  Future<String?> getAccessToken() async {
    try {
      if (_usePrefs) {
        final prefs = await SharedPreferences.getInstance();
        return prefs.getString(_accessKey);
      }
      return await _storage.read(key: _accessKey).timeout(_storageTimeout);
    } catch (_) {
      return null;
    }
  }

  Future<String?> _getRefreshToken() async {
    try {
      if (_usePrefs) {
        final prefs = await SharedPreferences.getInstance();
        return prefs.getString(_refreshKey);
      }
      return await _storage.read(key: _refreshKey).timeout(_storageTimeout);
    } catch (_) {
      return null;
    }
  }

  Future<bool> hasSession() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }

  Future<Map<String, dynamic>> get(String path, {bool auth = true}) =>
      _request('GET', path, auth: auth);

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) =>
      _request('POST', path, body: body, auth: auth);

  Future<Map<String, dynamic>> put(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) =>
      _request('PUT', path, body: body, auth: auth);

  Future<Map<String, dynamic>> delete(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) =>
      _request('DELETE', path, body: body, auth: auth);

  Future<Map<String, dynamic>> _request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
    bool retried = false,
    bool connectionRetried = false,
  }) async {
    final headers = <String, dynamic>{'Accept': 'application/json'};
    if (auth) {
      final token = await getAccessToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    // Do not reuse a half-closed keep-alive socket. A dead pooled connection
    // makes the next call fail in openUrl as a 12s connection timeout, and
    // the request never reaches the API.
    final options = Options(
      method: method,
      headers: headers,
      persistentConnection: false,
    );
    final Response res;
    try {
      if (method == 'GET') {
        res = await _dio.get(path, options: options);
      } else if (method == 'PUT') {
        res = await _dio.put(path, data: body, options: options);
      } else if (method == 'DELETE') {
        res = await _dio.delete(path, data: body, options: options);
      } else {
        res = await _dio.post(path, data: body, options: options);
      }
    } on DioException catch (e) {
      if (!connectionRetried && _isConnectFailure(e)) {
        _recycleTransport();
        return _request(
          method,
          path,
          body: body,
          auth: auth,
          retried: retried,
          connectionRetried: true,
        );
      }
      throw ApiException(offlineMessage);
    }

    if (auth && res.statusCode == 401 && !retried) {
      final ok = await _refresh();
      if (ok) {
        return _request(
          method,
          path,
          body: body,
          auth: auth,
          retried: true,
          connectionRetried: connectionRetried,
        );
      }
      await clearTokens();
      throw ApiException('Session expired. Please login again.', statusCode: 401);
    }

    final data = res.data is Map<String, dynamic> ? res.data as Map<String, dynamic> : <String, dynamic>{};
    final code = res.statusCode ?? 0;
    if (code >= 200 && code < 300) return data;
    throw ApiException.fromBody(code, data);
  }

  bool _isConnectFailure(DioException e) {
    return e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.connectionError;
  }

  /// Drop a stuck HTTP client and open a fresh one. Skips test adapters.
  void _recycleTransport() {
    final adapterName = _dio.httpClientAdapter.runtimeType.toString();
    if (adapterName != 'IOHttpClientAdapter' &&
        adapterName != 'BrowserHttpClientAdapter') {
      return;
    }
    final fresh = Dio(
      BaseOptions(
        baseUrl: _dio.options.baseUrl,
        connectTimeout: _dio.options.connectTimeout,
        receiveTimeout: _dio.options.receiveTimeout,
        headers: _dio.options.headers,
        validateStatus: (_) => true,
      ),
    );
    final previous = _dio.httpClientAdapter;
    _dio.httpClientAdapter = fresh.httpClientAdapter;
    previous.close(force: true);
  }

  Future<bool> _refresh() async {
    final refresh = await _getRefreshToken();
    if (refresh == null || refresh.isEmpty) return false;
    final res = await _dio.post(ApiConfig.tokenRefresh, data: {'refresh': refresh});
    if (res.statusCode != 200 || res.data is! Map) return false;
    final data = res.data as Map<String, dynamic>;
    final access = data['access'] as String?;
    final newRefresh = data['refresh'] as String?;
    if (access == null || newRefresh == null) return false;
    await saveTokens(access: access, refresh: newRefresh);
    return true;
  }
}
