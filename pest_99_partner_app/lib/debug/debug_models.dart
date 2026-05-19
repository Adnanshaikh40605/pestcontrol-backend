import 'package:flutter/foundation.dart';

enum DebugLogCategory {
  api,
  error,
  warning,
  navigation,
  auth,
  network,
  upload,
}

enum DebugLogFilter {
  all,
  errorsOnly,
  apiOnly,
  warnings,
  navigation,
  auth,
}

enum ApiRequestStatus { loading, success, failure }

@immutable
class DebugLogEntry {
  const DebugLogEntry({
    required this.id,
    required this.timestamp,
    required this.category,
    required this.title,
    this.message,
    this.stackTrace,
    this.metadata,
  });

  final String id;
  final DateTime timestamp;
  final DebugLogCategory category;
  final String title;
  final String? message;
  final String? stackTrace;
  final Map<String, dynamic>? metadata;
}

@immutable
class ApiRequestRecord {
  const ApiRequestRecord({
    required this.id,
    required this.method,
    required this.url,
    required this.startedAt,
    this.statusCode,
    this.duration,
    this.requestBody,
    this.responseBody,
    this.requestHeaders,
    this.errorMessage,
    this.status = ApiRequestStatus.loading,
    this.isMultipart = false,
    this.uploadSent,
    this.uploadTotal,
    this.retryCount = 0,
  });

  final String id;
  final String method;
  final String url;
  final DateTime startedAt;
  final int? statusCode;
  final Duration? duration;
  final String? requestBody;
  final String? responseBody;
  final Map<String, String>? requestHeaders;
  final String? errorMessage;
  final ApiRequestStatus status;
  final bool isMultipart;
  final int? uploadSent;
  final int? uploadTotal;
  final int retryCount;

  bool get isError =>
      status == ApiRequestStatus.failure ||
      (statusCode != null && statusCode! >= 400);

  ApiRequestRecord copyWith({
    int? statusCode,
    Duration? duration,
    String? responseBody,
    String? errorMessage,
    ApiRequestStatus? status,
    int? uploadSent,
    int? uploadTotal,
    int? retryCount,
  }) {
    return ApiRequestRecord(
      id: id,
      method: method,
      url: url,
      startedAt: startedAt,
      statusCode: statusCode ?? this.statusCode,
      duration: duration ?? this.duration,
      requestBody: requestBody,
      responseBody: responseBody ?? this.responseBody,
      requestHeaders: requestHeaders,
      errorMessage: errorMessage ?? this.errorMessage,
      status: status ?? this.status,
      isMultipart: isMultipart,
      uploadSent: uploadSent ?? this.uploadSent,
      uploadTotal: uploadTotal ?? this.uploadTotal,
      retryCount: retryCount ?? this.retryCount,
    );
  }
}

@immutable
class NetworkStatusInfo {
  const NetworkStatusInfo({
    required this.isConnected,
    this.label = 'Unknown',
    this.lastChecked,
  });

  final bool isConnected;
  final String label;
  final DateTime? lastChecked;
}
