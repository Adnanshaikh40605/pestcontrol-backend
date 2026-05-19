import 'package:flutter/foundation.dart';

import 'debug_config.dart';
import 'debug_models.dart';

class DebugLogStore extends ChangeNotifier {
  DebugLogStore._();
  static final DebugLogStore instance = DebugLogStore._();

  static const int maxRequests = 100;
  static const int maxLogs = 300;

  final List<DebugLogEntry> _logs = [];
  final List<ApiRequestRecord> _requests = [];
  final Map<String, ApiRequestRecord> _pending = {};
  DebugLogFilter _filter = DebugLogFilter.all;
  NetworkStatusInfo _network = const NetworkStatusInfo(isConnected: true, label: 'Unknown');
  String? _currentRoute;
  int _activeLoading = 0;

  DebugLogFilter get filter => _filter;
  NetworkStatusInfo get network => _network;
  String? get currentRoute => _currentRoute;
  int get activeLoading => _activeLoading;

  List<DebugLogEntry> get logs => List.unmodifiable(_logs);
  List<ApiRequestRecord> get requests => List.unmodifiable(_requests);

  List<DebugLogEntry> get filteredLogs {
    switch (_filter) {
      case DebugLogFilter.errorsOnly:
        return _logs.where((e) => e.category == DebugLogCategory.error).toList();
      case DebugLogFilter.apiOnly:
        return _logs.where((e) => e.category == DebugLogCategory.api).toList();
      case DebugLogFilter.warnings:
        return _logs.where((e) => e.category == DebugLogCategory.warning).toList();
      case DebugLogFilter.navigation:
        return _logs.where((e) => e.category == DebugLogCategory.navigation).toList();
      case DebugLogFilter.auth:
        return _logs.where((e) => e.category == DebugLogCategory.auth).toList();
      case DebugLogFilter.all:
        return List.unmodifiable(_logs);
    }
  }

  List<ApiRequestRecord> get errorRequests =>
      _requests.where((r) => r.isError).toList(growable: false);

  List<ApiRequestRecord> get pendingRequests =>
      _pending.values.toList(growable: false);

  void setFilter(DebugLogFilter filter) {
    if (!DebugConfig.enabled) return;
    _filter = filter;
    notifyListeners();
  }

  void setNetwork(NetworkStatusInfo info) {
    if (!DebugConfig.enabled) return;
    _network = info;
    notifyListeners();
  }

  void setCurrentRoute(String? route) {
    if (!DebugConfig.enabled) return;
    _currentRoute = route;
    notifyListeners();
  }

  String registerRequest({
    required String method,
    required String url,
    String? requestBody,
    Map<String, String>? headers,
    bool isMultipart = false,
  }) {
    if (!DebugConfig.enabled) return '';
    final id = '${DateTime.now().microsecondsSinceEpoch}';
    final record = ApiRequestRecord(
      id: id,
      method: method,
      url: url,
      startedAt: DateTime.now(),
      requestBody: requestBody,
      requestHeaders: headers,
      status: ApiRequestStatus.loading,
      isMultipart: isMultipart,
    );
    _pending[id] = record;
    _activeLoading = _pending.length;
    _insertRequest(record);
    _addLog(
      category: DebugLogCategory.api,
      title: '→ $method $url',
      message: requestBody,
    );
    notifyListeners();
    return id;
  }

  void completeRequest({
    required String id,
    int? statusCode,
    String? responseBody,
    String? errorMessage,
    Duration? duration,
  }) {
    if (!DebugConfig.enabled || id.isEmpty) return;
    final pending = _pending.remove(id);
    if (pending == null) return;
    _activeLoading = _pending.length;
    final success = statusCode != null && statusCode >= 200 && statusCode < 300;
    final updated = pending.copyWith(
      statusCode: statusCode,
      responseBody: responseBody,
      errorMessage: errorMessage,
      duration: duration,
      status: success ? ApiRequestStatus.success : ApiRequestStatus.failure,
    );
    _replaceRequest(updated);
    _addLog(
      category: success ? DebugLogCategory.api : DebugLogCategory.error,
      title: success
          ? '✓ ${pending.method} ${pending.url} ($statusCode)'
          : '✗ ${pending.method} ${pending.url} ($statusCode)',
      message: errorMessage ?? responseBody,
      metadata: {'requestId': id, 'statusCode': statusCode},
    );
    notifyListeners();
  }

  void failRequest({
    required String id,
    required String error,
    int? statusCode,
    String? responseBody,
    Duration? duration,
    int? retryCount,
  }) {
    if (!DebugConfig.enabled || id.isEmpty) return;
    final pending = _pending.remove(id);
    if (pending == null) return;
    _activeLoading = _pending.length;
    final updated = pending.copyWith(
      statusCode: statusCode,
      responseBody: responseBody,
      errorMessage: error,
      duration: duration,
      status: ApiRequestStatus.failure,
      retryCount: retryCount ?? pending.retryCount,
    );
    _replaceRequest(updated);
    _addLog(
      category: DebugLogCategory.error,
      title: '✗ ${pending.method} ${pending.url}',
      message: error,
      metadata: {'requestId': id, 'statusCode': statusCode},
    );
    notifyListeners();
  }

  void updateUploadProgress(String requestId, int sent, int total) {
    if (!DebugConfig.enabled || requestId.isEmpty) return;
    final pending = _pending[requestId];
    if (pending == null) return;
    _pending[requestId] = pending.copyWith(uploadSent: sent, uploadTotal: total);
    _replaceRequest(_pending[requestId]!);
    notifyListeners();
  }

  void logNavigation(String message, {String? from, String? to}) {
    _addLog(
      category: DebugLogCategory.navigation,
      title: message,
      message: to != null ? '→ $to' : null,
      metadata: {if (from != null) 'from': from, if (to != null) 'to': to},
    );
  }

  void logAuth(String title, {String? message}) {
    _addLog(category: DebugLogCategory.auth, title: title, message: message);
  }

  void logWarning(String title, {String? message}) {
    _addLog(category: DebugLogCategory.warning, title: title, message: message);
  }

  void logUpload(String title, {String? message}) {
    _addLog(category: DebugLogCategory.upload, title: title, message: message);
  }

  void logFlutterError(FlutterErrorDetails details) {
    _addLog(
      category: DebugLogCategory.error,
      title: 'FlutterError: ${details.exceptionAsString()}',
      message: details.summary.toString(),
      stackTrace: details.stack?.toString(),
    );
  }

  void logZoneError(Object error, StackTrace stack) {
    _addLog(
      category: DebugLogCategory.error,
      title: 'Uncaught: $error',
      stackTrace: stack.toString(),
    );
  }

  void logDioError(String title, {String? message, int? statusCode}) {
    _addLog(
      category: DebugLogCategory.error,
      title: title,
      message: message,
      metadata: {if (statusCode != null) 'statusCode': statusCode},
    );
  }

  String exportLogs() {
    final buffer = StringBuffer()
      ..writeln('=== Pest 99 Partner Debug Export ===')
      ..writeln('Generated: ${DateTime.now().toIso8601String()}')
      ..writeln('Route: $_currentRoute')
      ..writeln('Network: ${_network.label} (connected=${_network.isConnected})')
      ..writeln('')
      ..writeln('--- API Requests (${_requests.length}) ---');

    for (final r in _requests.reversed) {
      buffer
        ..writeln('[${r.startedAt.toIso8601String()}] ${r.method} ${r.url}')
        ..writeln('  status=${r.statusCode} duration=${r.duration?.inMilliseconds}ms')
        ..writeln('  request=${r.requestBody ?? ''}')
        ..writeln('  response=${r.responseBody ?? r.errorMessage ?? ''}')
        ..writeln('');
    }

    buffer.writeln('--- Logs (${_logs.length}) ---');
    for (final l in _logs.reversed) {
      buffer
        ..writeln('[${l.timestamp.toIso8601String()}] [${l.category.name}] ${l.title}')
        ..writeln(l.message ?? '')
        ..writeln(l.stackTrace ?? '')
        ..writeln('');
    }
    return buffer.toString();
  }

  void clear() {
    if (!DebugConfig.enabled) return;
    _logs.clear();
    _requests.clear();
    _pending.clear();
    _activeLoading = 0;
    notifyListeners();
  }

  void _addLog({
    required DebugLogCategory category,
    required String title,
    String? message,
    String? stackTrace,
    Map<String, dynamic>? metadata,
  }) {
    if (!DebugConfig.enabled) return;
    _logs.insert(
      0,
      DebugLogEntry(
        id: '${DateTime.now().microsecondsSinceEpoch}',
        timestamp: DateTime.now(),
        category: category,
        title: title,
        message: message,
        stackTrace: stackTrace,
        metadata: metadata,
      ),
    );
    if (_logs.length > maxLogs) {
      _logs.removeRange(maxLogs, _logs.length);
    }
    notifyListeners();
  }

  void _insertRequest(ApiRequestRecord record) {
    _requests.insert(0, record);
    if (_requests.length > maxRequests) {
      _requests.removeRange(maxRequests, _requests.length);
    }
  }

  void _replaceRequest(ApiRequestRecord record) {
    final i = _requests.indexWhere((r) => r.id == record.id);
    if (i >= 0) {
      _requests[i] = record;
    }
  }
}
