import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import '../config/api_config.dart';
import 'api_exception.dart';
import 'secure_token_storage.dart';
import 'session_coordinator.dart';

class ApiClient {
  ApiClient({
    Dio? dio,
    SecureTokenStorage? tokenStorage,
    SessionCoordinator? sessionCoordinator,
  })  : _tokens = tokenStorage ?? SecureTokenStorage(),
        _session = sessionCoordinator,
        _dio = dio ?? _createDio();

  final Dio _dio;
  final SecureTokenStorage _tokens;
  final SessionCoordinator? _session;
  bool _refreshing = false;
  Completer<bool>? _refreshCompleter;

  static Dio _createDio() {
    return Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Accept': 'application/json'},
        responseType: ResponseType.json,
        validateStatus: (_) => true,
      ),
    );
  }

  Future<void> saveSessionTokens({
    required String access,
    required String refresh,
    required String authType,
  }) async {
    await _tokens.saveTokens(access: access, refresh: refresh, authType: authType);
  }

  Future<void> clearSession() => _tokens.clearAll();
  Future<bool> hasSession() => _tokens.hasSession();

  Future<Map<String, dynamic>> get(String path, {bool auth = true}) {
    return _request((options) => _dio.get(path, options: options), path: path, auth: auth);
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) {
    return _request(
      (options) => _dio.post(path, data: body, options: options),
      path: path,
      method: 'POST',
      auth: auth,
    );
  }

  Future<Map<String, dynamic>> _request(
    Future<Response<dynamic>> Function(Options options) call, {
    required String path,
    String method = 'GET',
    bool auth = true,
  }) async {
    final options = Options(headers: <String, dynamic>{});
    if (auth) {
      final token = await _tokens.getAccessToken();
      if (token == null || token.isEmpty) {
        throw ApiException('Not logged in.');
      }
      options.headers!['Authorization'] = 'Bearer $token';
    }

    var response = await call(options);
    if (auth && response.statusCode == 401) {
      final refreshed = await _refreshToken();
      if (refreshed) {
        final token = await _tokens.getAccessToken();
        options.headers!['Authorization'] = 'Bearer $token';
        response = await call(options);
      }
    }

    return _parse(response, path: path, method: method);
  }

  Future<bool> _refreshToken() async {
    if (_refreshing) {
      return _refreshCompleter?.future ?? Future.value(false);
    }
    _refreshing = true;
    _refreshCompleter = Completer<bool>();

    try {
      final refresh = await _tokens.getRefreshToken();
      final authType = await _tokens.getAuthType() ?? 'partner';
      if (refresh == null || refresh.isEmpty) {
        _refreshCompleter!.complete(false);
        return false;
      }

      final response = await _dio.post(
        ApiConfig.tokenRefresh,
        data: {'refresh': refresh, 'auth_type': authType},
      );
      final data = _parse(response, path: ApiConfig.tokenRefresh, method: 'POST');
      final access = data['access'] as String?;
      final newRefresh = data['refresh'] as String? ?? refresh;
      if (access == null) {
        _refreshCompleter!.complete(false);
        return false;
      }
      await saveSessionTokens(access: access, refresh: newRefresh, authType: authType);
      _refreshCompleter!.complete(true);
      return true;
    } catch (_) {
      await clearSession();
      _session?.notifySessionExpired();
      _refreshCompleter?.complete(false);
      return false;
    } finally {
      _refreshing = false;
    }
  }

  Map<String, dynamic> _parse(Response<dynamic> response, {required String path, required String method}) {
    final status = response.statusCode ?? 0;
    dynamic body = response.data;
    if (body is String && body.isNotEmpty) {
      try {
        body = jsonDecode(body);
      } catch (_) {}
    }

    if (status >= 200 && status < 300) {
      if (body is Map<String, dynamic>) return body;
      return {'data': body};
    }

    String message = 'Request failed ($status)';
    if (body is Map<String, dynamic>) {
      message = (body['error'] ?? body['detail'] ?? message).toString();
    }
    if (status == 401) {
      _session?.notifySessionExpired();
    }
    throw ApiException(message, statusCode: status);
  }
}
