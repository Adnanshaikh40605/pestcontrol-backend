import 'api_exception.dart';

/// User-facing message from any caught error (production-safe, no stack traces).
String userErrorMessage(Object error, {String fallback = 'Something went wrong. Please try again.'}) {
  if (error is ApiException) return error.message;
  final text = error.toString();
  if (text.contains('SocketException') || text.contains('Connection')) {
    return 'Network error. Check your connection and try again.';
  }
  return fallback;
}
