class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.code});

  final String message;
  final int? statusCode;
  final String? code;

  @override
  String toString() => message;

  static ApiException fromBody(int status, Map<String, dynamic>? body) {
    if (body == null) return ApiException('Request failed ($status)', statusCode: status);
    final error = body['error'] ?? body['message'] ?? body['detail'];
    if (error is String) {
      return ApiException(error, statusCode: status, code: body['code'] as String?);
    }
    final errors = body['errors'];
    if (errors is Map) {
      for (final v in errors.values) {
        if (v is List && v.isNotEmpty) {
          return ApiException('${v.first}', statusCode: status);
        }
      }
    }
    return ApiException('Request failed ($status)', statusCode: status);
  }
}
