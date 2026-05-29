import 'package:dio/dio.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.code, this.retryAfterSeconds});

  final String message;
  final int? statusCode;
  final String? code;
  /// From HTTP Retry-After header when status is 429.
  final int? retryAfterSeconds;

  @override
  String toString() => message;

  static ApiException fromResponse(
    int status,
    Map<String, dynamic>? body, {
    int? retryAfterSeconds,
  }) {
    if (body == null) {
      return ApiException(
        _messageForStatus(status),
        statusCode: status,
        retryAfterSeconds: retryAfterSeconds,
      );
    }
    final error = body['error'] ?? body['message'] ?? body['detail'];
    if (error is String) {
      final parsedRetry = retryAfterSeconds ?? _parseThrottleWaitSeconds(error);
      return ApiException(
        error,
        statusCode: status,
        code: body['code'] as String?,
        retryAfterSeconds: parsedRetry,
      );
    }
    if (error is Map) {
      final first = error.values.first;
      if (first is List && first.isNotEmpty) {
        return ApiException('${first.first}', statusCode: status);
      }
    }
    final errors = body['errors'];
    if (errors is Map) {
      for (final v in errors.values) {
        if (v is List && v.isNotEmpty) {
          return ApiException('${v.first}', statusCode: status);
        }
      }
    }
    return ApiException(
      _messageForStatus(status),
      statusCode: status,
      retryAfterSeconds: retryAfterSeconds,
    );
  }

  static String _messageForStatus(int status) {
    if (status == 429) {
      return 'Too many requests. Please wait and try again.';
    }
    return 'Request failed ($status)';
  }

  /// DRF: "Request was throttled. Expected available in 651 seconds."
  static int? _parseThrottleWaitSeconds(String message) {
    final match = RegExp(
      r'expected available in (\d+) seconds',
      caseSensitive: false,
    ).firstMatch(message);
    if (match == null) return null;
    return int.tryParse(match.group(1)!);
  }

  static ApiException fromDio(DioException e) {
    final res = e.response;
    if (res != null) {
      Map<String, dynamic>? body;
      final data = res.data;
      if (data is Map<String, dynamic>) body = data;
      return fromResponse(res.statusCode ?? 0, body);
    }
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException('Network slow. Please try again.', statusCode: 408);
      case DioExceptionType.connectionError:
        return ApiException('Network error. Check your connection.');
      case DioExceptionType.cancel:
        return ApiException('Request cancelled.');
      default:
        return ApiException(e.message ?? 'Network error. Check your connection.');
    }
  }
}
