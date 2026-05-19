import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../core/routing/app_router.dart';
import 'debug_config.dart';
import 'debug_utils.dart';

/// Shows a debug-only dialog for backend HTTP errors (400–500).
class DebugBackendAlert {
  DebugBackendAlert._();

  static final Set<int> _alertStatuses = {400, 401, 403, 404, 500};
  static bool _showing = false;

  static void showIfNeeded(DioException error) {
    if (!DebugConfig.enabled || _showing) return;
    final status = error.response?.statusCode;
    if (status == null || !_alertStatuses.contains(status)) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctx = rootNavigatorKey.currentContext;
      if (ctx == null || !ctx.mounted) return;
      _showing = true;
      showDialog<void>(
        context: ctx,
        builder: (context) => _BackendErrorDialog(
          statusCode: status,
          endpoint: error.requestOptions.uri.toString(),
          method: error.requestOptions.method,
          payload: DebugUtils.formatResponse(error.response?.data),
          message: error.message ?? 'Request failed',
        ),
      ).whenComplete(() => _showing = false);
    });
  }

  static void showForStatus({
    required int statusCode,
    required String endpoint,
    required String method,
    String? message,
    String? payload,
  }) {
    if (!DebugConfig.enabled || _showing) return;
    if (!_alertStatuses.contains(statusCode)) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctx = rootNavigatorKey.currentContext;
      if (ctx == null || !ctx.mounted) return;
      _showing = true;
      showDialog<void>(
        context: ctx,
        builder: (context) => _BackendErrorDialog(
          statusCode: statusCode,
          endpoint: endpoint,
          method: method,
          payload: payload ?? '',
          message: message ?? 'Request failed',
        ),
      ).whenComplete(() => _showing = false);
    });
  }
}

class _BackendErrorDialog extends StatelessWidget {
  const _BackendErrorDialog({
    required this.statusCode,
    required this.endpoint,
    required this.method,
    required this.payload,
    required this.message,
  });

  final int statusCode;
  final String endpoint;
  final String method;
  final String payload;
  final String message;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Backend error ($statusCode)'),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('$method $endpoint', style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text(message),
            if (payload.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text('Response', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              SelectableText(
                payload,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Dismiss')),
      ],
    );
  }
}
