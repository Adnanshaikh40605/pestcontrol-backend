import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/api_config.dart';
import '../debug/debug_backend_alert.dart';
import '../debug/debug_config.dart';
import '../debug/debug_dio_interceptor.dart';
import '../debug/debug_log_store.dart';
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

  static const _sessionExpiredMessage = 'Session expired. Please login again.';

  static Dio _createDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        sendTimeout: const Duration(seconds: 60),
        headers: {'Accept': 'application/json'},
        responseType: ResponseType.json,
        validateStatus: (_) => true,
      ),
    );
    if (DebugConfig.enabled) {
      dio.interceptors.add(DebugDioInterceptor());
    }
    return dio;
  }

  Future<void> saveSessionTokens({
    required String access,
    required String refresh,
  }) async {
    await _tokens.saveTokens(access: access, refresh: refresh);
    if (DebugConfig.enabled) {
      DebugLogStore.instance.logAuth('Tokens saved (secure)');
    }
  }

  Future<void> clearSession() async {
    await _tokens.clearAll();
    if (DebugConfig.enabled) {
      DebugLogStore.instance.logAuth('Session cleared');
    }
  }

  Future<String?> getAccessToken() => _tokens.getAccessToken();

  Future<bool> hasSession() => _tokens.hasSession();

  Future<Map<String, dynamic>> get(String path, {bool auth = true}) async {
    return _request(
      (options) => _dio.get(path, options: options),
      path: path,
      method: 'GET',
      auth: auth,
    );
  }

  Future<Map<String, dynamic>> put(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) async {
    return _request(
      (options) => _dio.put(path, data: body, options: options),
      path: path,
      method: 'PUT',
      auth: auth,
    );
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) async {
    return _request(
      (options) => _dio.post(path, data: body, options: options),
      path: path,
      method: 'POST',
      auth: auth,
    );
  }

  Future<Map<String, dynamic>> postMultipart(
    String path, {
    Map<String, String>? fields,
    Map<String, String>? files,
    bool auth = true,
  }) async {
    final formData = await _buildFormData(fields: fields, files: files);
    return _request(
      (options) => _dio.post(
        path,
        data: formData,
        options: options,
        onSendProgress: (sent, total) {
          if (DebugConfig.enabled) {
            final pending = DebugLogStore.instance.pendingRequests;
            if (pending.isNotEmpty) {
              DebugLogStore.instance.updateUploadProgress(pending.first.id, sent, total);
            }
          }
        },
      ),
      path: path,
      method: 'POST',
      auth: auth,
      json: false,
    );
  }

  Future<Map<String, dynamic>> putMultipart(
    String path, {
    Map<String, String>? fields,
    Map<String, String>? files,
    bool auth = true,
  }) async {
    final formData = await _buildFormData(fields: fields, files: files);
    return _request(
      (options) => _dio.put(
        path,
        data: formData,
        options: options,
        onSendProgress: (sent, total) {
          if (DebugConfig.enabled) {
            DebugLogStore.instance.logUpload(
              'Upload $path',
              message: '$sent / $total bytes',
            );
          }
        },
      ),
      path: path,
      method: 'PUT',
      auth: auth,
      json: false,
    );
  }

  Future<FormData> _buildFormData({
    Map<String, String>? fields,
    Map<String, String>? files,
  }) async {
    final map = <String, dynamic>{};
    if (fields != null) map.addAll(fields);
    if (files != null) {
      for (final entry in files.entries) {
        final file = File(entry.value);
        map[entry.key] = await MultipartFile.fromFile(
          file.path,
          filename: entry.value.split(Platform.pathSeparator).last,
        );
      }
    }
    return FormData.fromMap(map);
  }

  Future<Map<String, dynamic>> _request(
    Future<Response<dynamic>> Function(Options options) call, {
    required String path,
    required String method,
    required bool auth,
    bool retried = false,
    bool json = true,
  }) async {
    try {
      final options = await _options(auth, json: json);
      final res = await call(options);
      if (auth && res.statusCode == 401 && !retried) {
        final refreshed = await _refreshTokens();
        if (refreshed) {
          return _request(
            call,
            path: path,
            method: method,
            auth: auth,
            retried: true,
            json: json,
          );
        }
        await _expireSession();
        throw ApiException(_sessionExpiredMessage, statusCode: 401);
      }
      return _decode(res, path: path, method: method);
    } on DioException catch (e) {
      if (e.response != null) {
        final res = e.response!;
        if (auth && res.statusCode == 401 && !retried) {
          final refreshed = await _refreshTokens();
          if (refreshed) {
            return _request(
              call,
              path: path,
              method: method,
              auth: auth,
              retried: true,
              json: json,
            );
          }
          await _expireSession();
          throw ApiException(_sessionExpiredMessage, statusCode: 401);
        }
        return _decode(res, path: path, method: method);
      }
      if (DebugConfig.enabled) {
        DebugLogStore.instance.logDioError('Network failure', message: e.message);
      }
      throw ApiException.fromDio(e);
    } on ApiException {
      rethrow;
    }
  }

  Future<bool> _refreshTokens() async {
    if (_refreshing) {
      return _refreshCompleter?.future ?? Future.value(false);
    }
    _refreshing = true;
    _refreshCompleter = Completer<bool>();

    try {
      final refresh = await _tokens.getRefreshToken();
      if (refresh == null || refresh.isEmpty) {
        _refreshCompleter!.complete(false);
        return false;
      }

      final res = await _dio.post(
        ApiConfig.tokenRefresh,
        data: {'refresh': refresh},
        options: Options(
          headers: {'Content-Type': 'application/json'},
          extra: {'skip_auth': true},
        ),
      );

      if (res.statusCode != 200) {
        _refreshCompleter!.complete(false);
        return false;
      }

      final data = res.data;
      if (data is! Map<String, dynamic>) {
        _refreshCompleter!.complete(false);
        return false;
      }

      final access = data['access'] as String?;
      final newRefresh = data['refresh'] as String? ?? refresh;
      if (access == null || access.isEmpty) {
        _refreshCompleter!.complete(false);
        return false;
      }

      await _tokens.saveTokens(access: access, refresh: newRefresh);
      if (DebugConfig.enabled) {
        DebugLogStore.instance.logAuth('Tokens refreshed');
      }
      _refreshCompleter!.complete(true);
      return true;
    } catch (e) {
      if (DebugConfig.enabled) {
        DebugLogStore.instance.logAuth('Refresh failed', message: '$e');
      }
      _refreshCompleter!.complete(false);
      return false;
    } finally {
      _refreshing = false;
    }
  }

  Future<void> _expireSession() async {
    await clearSession();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('partner_app_approved');
    _session?.notifySessionExpired(_sessionExpiredMessage);
  }

  Future<Options> _options(bool auth, {bool json = true}) async {
    final headers = <String, dynamic>{};
    if (json) headers['Content-Type'] = 'application/json';
    if (auth) {
      final token = await getAccessToken();
      if (token == null || token.isEmpty) {
        if (DebugConfig.enabled) {
          DebugLogStore.instance.logAuth('Missing access token');
        }
        throw ApiException(_sessionExpiredMessage, statusCode: 401);
      }
      headers['Authorization'] = 'Bearer $token';
    }
    return Options(headers: headers);
  }

  Map<String, dynamic> _decode(
    Response<dynamic> res, {
    required String path,
    required String method,
  }) {
    final status = res.statusCode ?? 0;
    Map<String, dynamic>? body;
    final data = res.data;
    if (data is Map<String, dynamic>) {
      body = data;
    } else if (data is String && data.isNotEmpty) {
      final decoded = jsonDecode(data);
      if (decoded is Map<String, dynamic>) body = decoded;
    }

    if (status >= 200 && status < 300) {
      return body ?? {};
    }

    final ex = ApiException.fromResponse(status, body);
    if (DebugConfig.enabled) {
      DebugBackendAlert.showForStatus(
        statusCode: status,
        endpoint: '${ApiConfig.baseUrl}$path',
        method: method,
        message: ex.message,
        payload: body != null ? jsonEncode(body) : '',
      );
    }
    throw ex;
  }

  void dispose() => _dio.close();
}
