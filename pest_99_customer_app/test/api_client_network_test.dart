import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/core/api_client.dart';
import 'package:pest_99_customer_app/core/api_exception.dart';

void main() {
  test('connection timeout becomes a customer message and retries once', () async {
    final adapter = _TimeoutThenOkAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'https://api.vacationbna.site'));
    dio.httpClientAdapter = adapter;
    final api = ApiClient(dio: dio);

    final data = await api.post(
      '/api/customer/otp/send/',
      auth: false,
      body: {
        'mobile': '9372792693',
        'purpose': 'website_booking',
        'full_name': 'Adnan',
      },
    );

    expect(data['delivery'], 'queued');
    expect(adapter.calls, 2);
    expect(adapter.paths, [
      '/api/customer/otp/send/',
      '/api/customer/otp/send/',
    ]);
    expect(adapter.sawPersistentFalse, isTrue);
  });

  test('a failed connection does not surface DioException', () async {
    final dio = Dio(BaseOptions(baseUrl: 'https://api.vacationbna.site'));
    dio.httpClientAdapter = _AlwaysConnectFailAdapter();
    final api = ApiClient(dio: dio);

    expect(
      () => api.post('/api/customer/otp/send/', auth: false, body: {'mobile': '9'}),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'message',
          ApiClient.offlineMessage,
        ),
      ),
    );
  });

  test('business errors stay the API message', () async {
    final dio = Dio(
      BaseOptions(
        baseUrl: 'https://api.vacationbna.site',
        validateStatus: (_) => true,
      ),
    );
    dio.httpClientAdapter = _JsonAdapter(
      status: 400,
      body: '{"error":"Please wait 30s before requesting another OTP.","code":"otp_cooldown"}',
    );
    final api = ApiClient(dio: dio);

    expect(
      () => api.post('/api/customer/otp/send/', auth: false, body: {'mobile': '9'}),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'message',
          'Please wait 30s before requesting another OTP.',
        ),
      ),
    );
  });
}

class _TimeoutThenOkAdapter implements HttpClientAdapter {
  int calls = 0;
  final paths = <String>[];
  bool sawPersistentFalse = false;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    calls += 1;
    paths.add(options.path);
    if (options.persistentConnection == false) sawPersistentFalse = true;
    if (calls == 1) {
      throw DioException.connectionTimeout(
        requestOptions: options,
        timeout: const Duration(seconds: 12),
      );
    }
    return ResponseBody.fromString(
      '{"message":"OTP sent successfully.","mobile":"9372792693","delivery":"queued"}',
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

class _AlwaysConnectFailAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    throw DioException.connectionTimeout(
      requestOptions: options,
      timeout: const Duration(seconds: 12),
    );
  }

  @override
  void close({bool force = false}) {}
}

class _JsonAdapter implements HttpClientAdapter {
  _JsonAdapter({required this.status, required this.body});

  final int status;
  final String body;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      body,
      status,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
