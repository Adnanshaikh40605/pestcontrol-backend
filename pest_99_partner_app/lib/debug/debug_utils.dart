import 'dart:convert';

import 'package:dio/dio.dart';

class DebugUtils {
  DebugUtils._();

  static const _sensitiveKeys = {
    'authorization',
    'cookie',
    'password',
    'access',
    'refresh',
    'token',
  };

  static Map<String, String> sanitizeHeaders(Map<String, dynamic>? headers) {
    if (headers == null) return {};
    final out = <String, String>{};
    headers.forEach((key, value) {
      final k = key.toLowerCase();
      if (_sensitiveKeys.any(k.contains)) {
        out[key] = _mask('$value');
      } else {
        out[key] = '$value';
      }
    });
    return out;
  }

  static String sanitizeBody(dynamic data) {
    if (data == null) return '';
    try {
      if (data is FormData) {
        final fields = data.fields.map((e) => '${e.key}=${e.value}').join(', ');
        final files = data.files.map((e) => '${e.key}=<file>').join(', ');
        return 'FormData(fields: [$fields], files: [$files])';
      }
      if (data is Map) {
        final copy = Map<String, dynamic>.from(data);
        for (final key in copy.keys.toList()) {
          if (_sensitiveKeys.any(key.toLowerCase().contains)) {
            copy[key] = _mask('${copy[key]}');
          }
        }
        return const JsonEncoder.withIndent('  ').convert(copy);
      }
      if (data is String) {
        final decoded = jsonDecode(data);
        if (decoded is Map) return sanitizeBody(decoded);
        return data.length > 4000 ? '${data.substring(0, 4000)}…' : data;
      }
      final text = data.toString();
      return text.length > 4000 ? '${text.substring(0, 4000)}…' : text;
    } catch (_) {
      final text = data.toString();
      return text.length > 4000 ? '${text.substring(0, 4000)}…' : text;
    }
  }

  static String formatResponse(dynamic data) {
    if (data == null) return '';
    try {
      if (data is Map || data is List) {
        return const JsonEncoder.withIndent('  ').convert(data);
      }
      if (data is String) {
        final decoded = jsonDecode(data);
        return const JsonEncoder.withIndent('  ').convert(decoded);
      }
    } catch (_) {}
    return sanitizeBody(data);
  }

  static String _mask(String value) {
    if (value.length <= 8) return '••••••••';
    return '${value.substring(0, 4)}…${value.substring(value.length - 4)}';
  }

  static DateTime? jwtExpiry(String? token) {
    if (token == null || token.isEmpty) return null;
    try {
      final parts = token.split('.');
      if (parts.length < 2) return null;
      var payload = parts[1];
      final mod = payload.length % 4;
      if (mod > 0) payload += '=' * (4 - mod);
      final decoded = utf8.decode(base64Url.decode(payload));
      final map = jsonDecode(decoded) as Map<String, dynamic>;
      final exp = map['exp'];
      if (exp is int) {
        return DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true).toLocal();
      }
    } catch (_) {}
    return null;
  }

  static String expiryLabel(DateTime? expiry) {
    if (expiry == null) return 'Unknown / not JWT';
    final now = DateTime.now();
    if (expiry.isBefore(now)) {
      return 'Expired ${now.difference(expiry).inMinutes}m ago';
    }
    return 'Expires in ${expiry.difference(now).inMinutes}m';
  }
}
