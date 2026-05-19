import 'package:dio/dio.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.code});

  final String message;
  final int? statusCode;
  final String? code;

  @override
  String toString() => message;

  static ApiException fromResponse(int status, Map<String, dynamic>? body) {
    if (body == null) {
      return ApiException('Request failed ($status)', statusCode: status);
    }
    final error = body['error'] ?? body['message'] ?? body['detail'];
    if (error is String) {
      return ApiException(error, statusCode: status, code: body['code'] as String?);
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
    return ApiException('Something went wrong. Please try again.', statusCode: status);
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
