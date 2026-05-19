import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import 'debug_backend_alert.dart';
import 'debug_config.dart';
import 'debug_log_store.dart';
import 'debug_utils.dart';

/// Dio interceptor — logs requests/responses/errors (debug builds only).
class DebugDioInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (!DebugConfig.enabled) {
      handler.next(options);
      return;
    }

    final url = options.uri.toString();
    final body = DebugUtils.sanitizeBody(options.data);
    final headers = DebugUtils.sanitizeHeaders(options.headers);
    final isMultipart = options.data is FormData;

    final id = DebugLogStore.instance.registerRequest(
      method: options.method,
      url: url,
      requestBody: body.isEmpty ? null : body,
      headers: headers,
      isMultipart: isMultipart,
    );
    options.extra['debug_request_id'] = id;
    options.extra['debug_start'] = DateTime.now();

    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    if (DebugConfig.enabled) {
      _finish(response.requestOptions, response: response);
    }
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (DebugConfig.enabled) {
      _finish(
        err.requestOptions,
        error: err,
        response: err.response,
      );
      DebugBackendAlert.showIfNeeded(err);
    }
    handler.next(err);
  }

  void _finish(
    RequestOptions options, {
    Response? response,
    DioException? error,
  }) {
    final id = options.extra['debug_request_id'] as String? ?? '';
    final start = options.extra['debug_start'] as DateTime?;
    final duration = start != null ? DateTime.now().difference(start) : null;
    final status = response?.statusCode ?? error?.response?.statusCode;
    final body = DebugUtils.formatResponse(response?.data ?? error?.response?.data);

    if (error != null && response == null) {
      DebugLogStore.instance.failRequest(
        id: id,
        error: error.message ?? error.type.name,
        statusCode: status,
        responseBody: body.isEmpty ? null : body,
        duration: duration,
        retryCount: options.extra['retry_count'] as int? ?? 0,
      );
      DebugLogStore.instance.logDioError(
        'Dio ${error.type.name}',
        message: error.message,
        statusCode: status,
      );
      return;
    }

    final success = status != null && status >= 200 && status < 300;
    if (success) {
      DebugLogStore.instance.completeRequest(
        id: id,
        statusCode: status,
        responseBody: body.isEmpty ? null : body,
        duration: duration,
      );
    } else {
      DebugLogStore.instance.failRequest(
        id: id,
        error: 'HTTP $status',
        statusCode: status,
        responseBody: body.isEmpty ? null : body,
        duration: duration,
      );
    }
  }
}

/// Tracks GoRouter / Navigator route changes.
class DebugRouteObserver extends NavigatorObserver {
  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _log('PUSH', route, previousRoute);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _log('POP', route, previousRoute);
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    if (newRoute != null) {
      _log('REPLACE', newRoute, oldRoute);
    }
  }

  void _log(String action, Route<dynamic> route, Route<dynamic>? previous) {
    if (!DebugConfig.enabled) return;
    final name = route.settings.name ?? route.settings.toString();
    final prev = previous?.settings.name;
    DebugLogStore.instance.setCurrentRoute(name);
    DebugLogStore.instance.logNavigation(
      '$action $name',
      from: prev,
      to: name,
    );
  }
}

/// Updates current route from GoRouter location string.
void debugSyncGoRoute(String location) {
  if (!DebugConfig.enabled) return;
  DebugLogStore.instance.setCurrentRoute(location);
}
