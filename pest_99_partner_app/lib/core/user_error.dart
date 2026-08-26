import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'api_exception.dart';

/// Maps any caught error to a short, user-safe message (no stack traces).
String userErrorMessage(
  Object error, {
  String fallback = 'Something went wrong. Please try again.',
}) {
  if (error is ApiException) {
    return _apiExceptionMessage(error);
  }
  if (error is DioException) {
    return userErrorMessage(ApiException.fromDio(error), fallback: fallback);
  }
  if (error is TimeoutException) {
    return 'Network slow. Please try again.';
  }
  if (error is SocketException) {
    return 'Network error. Check your connection and try again.';
  }
  if (error is FormatException || error is TypeError) {
    return 'Could not read the server response. Please try again.';
  }

  final text = error.toString();
  if (text.isEmpty || text == 'null') return fallback;

  // Never surface raw Exception: / Error: prefixes or long dumps.
  final cleaned = text
      .replaceFirst(RegExp(r'^(Exception|Error):\s*'), '')
      .replaceFirst(RegExp(r'^ApiException:\s*'), '')
      .trim();

  if (cleaned.contains('SocketException') ||
      cleaned.contains('Connection refused') ||
      cleaned.contains('Network is unreachable') ||
      cleaned.contains('Failed host lookup')) {
    return 'Network error. Check your connection and try again.';
  }
  if (cleaned.contains('TimeoutException') ||
      cleaned.contains('timed out') ||
      cleaned.contains('Timeout')) {
    return 'Network slow. Please try again.';
  }
  if (cleaned.contains('HandshakeException') || cleaned.contains('CERTIFICATE')) {
    return 'Secure connection failed. Please try again.';
  }

  // Avoid dumping Framework / Dio internals in production UI.
  if (!kDebugMode &&
      (cleaned.length > 160 ||
          cleaned.contains('package:') ||
          cleaned.contains('DioException') ||
          cleaned.contains('#'))) {
    return fallback;
  }

  return cleaned.isEmpty ? fallback : cleaned;
}

String _apiExceptionMessage(ApiException e) {
  final code = e.code;
  if (code == 'cancelled_in_crm') {
    return e.message.isNotEmpty
        ? e.message
        : 'This booking was already cancelled from CRM.';
  }
  if (code == 'already_accepted') {
    return e.message.isNotEmpty
        ? e.message
        : 'This booking was already accepted by another technician.';
  }
  if (code == 'already_completed') {
    return e.message.isNotEmpty ? e.message : 'This job is already completed.';
  }
  if (code == 'already_started') {
    return e.message.isNotEmpty ? e.message : 'This job was already started.';
  }
  if (code == 'not_started') {
    return e.message.isNotEmpty
        ? e.message
        : 'Start the job with a selfie before ending service.';
  }
  if (code == 'suspended') {
    return e.message.isNotEmpty
        ? e.message
        : 'Your account is suspended. Contact CRM admin.';
  }
  if (code == 'no_technician_link') {
    return e.message.isNotEmpty
        ? e.message
        : 'Your profile is not linked. Contact CRM admin.';
  }
  if (code == 'selfie_required' || code == 'invalid_selfie') {
    return e.message.isNotEmpty
        ? e.message
        : 'A clear selfie is required to start the job.';
  }
  if (code == 'invalid_payment') {
    return e.message.isNotEmpty
        ? e.message
        : 'Choose Cash or Online payment to end service.';
  }
  if (code == 'complete_failed') {
    return e.message.isNotEmpty
        ? e.message
        : 'Could not complete this booking. Please try again.';
  }

  if (e.statusCode == 401) {
    return e.message.isNotEmpty ? e.message : 'Session expired. Please login again.';
  }
  if (e.statusCode == 403) {
    return e.message.isNotEmpty
        ? e.message
        : 'You do not have permission for this action.';
  }
  if (e.statusCode == 404) {
    return e.message.isNotEmpty ? e.message : 'This booking is no longer available.';
  }
  if (e.statusCode == 408) {
    return 'Network slow. Please try again.';
  }
  if (e.statusCode == 429) {
    if (e.retryAfterSeconds != null) {
      return 'Too many requests. Try again in ${e.retryAfterSeconds} seconds.';
    }
    return e.message.isNotEmpty
        ? e.message
        : 'Too many requests. Please wait a minute and try again.';
  }
  if (e.statusCode != null && e.statusCode! >= 500) {
    return e.message.isNotEmpty && !e.message.startsWith('Request failed')
        ? e.message
        : 'Server error. Please try again in a moment.';
  }

  return e.message.isNotEmpty ? e.message : 'Something went wrong. Please try again.';
}
