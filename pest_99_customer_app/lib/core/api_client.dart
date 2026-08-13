import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

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

  static Dio _createDio() {
    return Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Accept': 'application/json'},
        validateStatus: (_) => true,
      ),
    );
  }

  Future<void> saveTokens({required String access, required String refresh}) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  Future<String?> getAccessToken() => _storage.read(key: _accessKey);

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
  }) async {
    final headers = <String, dynamic>{'Accept': 'application/json'};
    if (auth) {
      final token = await getAccessToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    final options = Options(method: method, headers: headers);
    final Response res;
    if (method == 'GET') {
      res = await _dio.get(path, options: options);
    } else if (method == 'PUT') {
      res = await _dio.put(path, data: body, options: options);
    } else if (method == 'DELETE') {
      res = await _dio.delete(path, data: body, options: options);
    } else {
      res = await _dio.post(path, data: body, options: options);
    }

    if (auth && res.statusCode == 401 && !retried) {
      final ok = await _refresh();
      if (ok) return _request(method, path, body: body, auth: auth, retried: true);
      await clearTokens();
      throw ApiException('Session expired. Please login again.', statusCode: 401);
    }

    final data = res.data is Map<String, dynamic> ? res.data as Map<String, dynamic> : <String, dynamic>{};
    final code = res.statusCode ?? 0;
    if (code >= 200 && code < 300) return data;
    throw ApiException.fromBody(code, data);
  }

  Future<bool> _refresh() async {
    final refresh = await _storage.read(key: _refreshKey);
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
