import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/core/api_client.dart';
import 'package:pest_99_customer_app/core/booking_form_density.dart';
import 'package:pest_99_customer_app/providers/auth_provider.dart';
import 'package:pest_99_customer_app/providers/booking_flow_provider.dart';
import 'package:pest_99_customer_app/screens/booking_flow_screens.dart';
import 'package:provider/provider.dart';

const _header = 48.0;
const _nav = 48.0;
const _bottomPad = 2.0;

double _contentWidth(double viewportWidth) => viewportWidth - 40;

BookingFormDensity _fit(double width, double height, {double safeTop = 0, double safeBottom = 0}) {
  final body = BookingFormDensity.bodyHeightForViewport(
    viewportHeight: height,
    safeTop: safeTop,
    safeBottom: safeBottom,
    headerHeight: _header,
    navigationBarHeight: _nav,
  );
  return BookingFormDensity.fit(
    bodyHeight: body,
    contentWidth: _contentWidth(width),
    shape: const BookingFormShape(),
    bottomPad: _bottomPad,
  );
}

void main() {
  const shape = BookingFormShape();

  group('booking form fills the viewport', () {
    const phones = <(String, double, double)>[
      ('Galaxy S8+', 360, 740),
      ('iPhone 16', 393, 852),
      ('iPhone 16 Pro Max', 440, 956),
    ];

    for (final phone in phones) {
      test('${phone.$1} fills the body with no dead gap', () {
        final body = BookingFormDensity.bodyHeightForViewport(
          viewportHeight: phone.$3,
        );
        final dens = _fit(phone.$2, phone.$3);
        final used = dens.occupied(shape, bottomPad: _bottomPad);
        expect(
          (body - used).abs(),
          lessThan(1),
          reason:
              'body=$body used=$used gap=${dens.gap} input=${dens.inputH} '
              'choice=${dens.choiceH} ctaGap=${dens.ctaGap}',
        );
        expect(dens.inputH, inInclusiveRange(36, 54));
        expect(dens.selectH, inInclusiveRange(36, 50));
        expect(dens.choiceH, inInclusiveRange(38, 62));
        expect(dens.ctaH, inInclusiveRange(42, 52));
        expect(dens.gap, inInclusiveRange(6, 22));
        expect(dens.priceH, greaterThanOrEqualTo(34));
      });
    }

    test('density grows from short phones to tall phones', () {
      final short = _fit(360, 740);
      final mid = _fit(393, 852);
      final tall = _fit(440, 956);
      expect(mid.inputH, greaterThan(short.inputH - 0.01));
      expect(tall.inputH, greaterThanOrEqualTo(mid.inputH));
      expect(mid.gap, greaterThan(short.gap));
      expect(tall.gap, greaterThan(mid.gap - 0.01));
      expect(tall.choiceH, greaterThanOrEqualTo(mid.choiceH));
      expect(tall.occupied(shape, bottomPad: _bottomPad), greaterThan(mid.occupied(shape, bottomPad: _bottomPad)));
    });

    test('iPhone safe areas still fill without a void', () {
      for (final phone in [(393.0, 852.0), (440.0, 956.0)]) {
        final body = BookingFormDensity.bodyHeightForViewport(
          viewportHeight: phone.$2,
          safeTop: 59,
          safeBottom: 34,
        );
        final dens = _fit(phone.$1, phone.$2, safeTop: 59, safeBottom: 34);
        final used = dens.occupied(shape, bottomPad: _bottomPad);
        expect((body - used).abs(), lessThan(1), reason: 'body=$body used=$used');
        expect(dens.inputH, greaterThanOrEqualTo(36));
        expect(dens.gap, greaterThanOrEqualTo(6));
      }
    });

    test('extra-short height keeps the compact floor and may scroll', () {
      final body = 500.0;
      final dens = BookingFormDensity.fit(
        bodyHeight: body,
        contentWidth: 320,
        shape: shape,
        bottomPad: _bottomPad,
      );
      final floor = BookingFormDensity.fit(
        bodyHeight: 200,
        contentWidth: 320,
        shape: shape,
        bottomPad: _bottomPad,
      );
      expect(dens.inputH, floor.inputH);
      expect(dens.gap, closeTo(floor.gap, 0.01));
      expect(dens.occupied(shape, bottomPad: _bottomPad), greaterThan(body));
    });

    test('hiding treatment and plan still fills instead of leaving a hole', () {
      const commercial = BookingFormShape(showTreatment: false, showPlan: false);
      final body = BookingFormDensity.bodyHeightForViewport(viewportHeight: 956);
      final dens = BookingFormDensity.fit(
        bodyHeight: body,
        contentWidth: 400,
        shape: commercial,
        bottomPad: _bottomPad,
      );
      expect(
        (body - dens.occupied(commercial, bottomPad: _bottomPad)).abs(),
        lessThan(1),
      );
    });

    test('narrow title uses a single-line size', () {
      final dens = _fit(360, 740);
      expect(dens.titleSize, lessThanOrEqualTo(14));
      expect(dens.titleLine, lessThan(20));
      expect(dens.warrantySize, lessThanOrEqualTo(10));
    });
  });

  group('rendered booking form', () {
    for (final phone in <(String, double, double)>[
      ('Galaxy S8+', 360, 740),
      ('iPhone 16', 393, 852),
      ('iPhone 16 Pro Max', 440, 956),
    ]) {
      testWidgets('${phone.$1} shows confirm above the nav without a void', (tester) async {
        tester.view.physicalSize = Size(phone.$2, phone.$3);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        final dio = Dio();
        dio.httpClientAdapter = _ImmediateAdapter();
        final api = ApiClient(dio: dio);

        await tester.pumpWidget(
          MultiProvider(
            providers: [
              Provider<ApiClient>.value(value: api),
              ChangeNotifierProvider(create: (_) => AuthProvider(api)),
              ChangeNotifierProvider(create: (_) => BookingFlowProvider()),
            ],
            child: const MaterialApp(
              home: Scaffold(
                body: WebsiteBookingScreen(embeddedInShell: true),
                bottomNavigationBar: SizedBox(height: _nav),
              ),
            ),
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(seconds: 9));

        expect(tester.takeException(), isNull);

        final confirm = find.text('Confirm Booking →');
        expect(confirm, findsOneWidget);
        final title = find.text('Confirm Your Booking');
        expect(title, findsOneWidget);
        expect(tester.getSize(title).height, lessThan(24));

        final confirmBox = tester.getRect(confirm);
        final viewportBottom = phone.$3 - _nav;
        expect(
          confirmBox.bottom,
          lessThanOrEqualTo(viewportBottom + 1),
          reason: 'Confirm must sit above the bottom nav',
        );
        expect(
          confirmBox.bottom,
          greaterThan(viewportBottom - 48),
          reason: 'Confirm should sit near the nav, not mid-page. bottom=${confirmBox.bottom}',
        );

        final name = tester.getRect(find.text('YOUR NAME *'));
        final price = tester.getRect(find.text('Select options for price'));
        final between = price.top - name.bottom;
        expect(
          between,
          lessThan(150),
          reason: 'Gap between name and price is $between (dead void)',
        );
        expect(between, greaterThan(30));

        expect(find.text('SELECT SERVICE *'), findsOneWidget);
        expect(find.text('PREMISE SIZE *'), findsOneWidget);
        expect(find.text('TREATMENT QUALITY *'), findsOneWidget);
        expect(find.text('SERVICE PLAN *'), findsOneWidget);
        expect(find.text('SERVICE ADDRESS *'), findsOneWidget);
        expect(find.text('PREFERRED DATE *'), findsOneWidget);
        expect(find.text('PREFERRED TIME *'), findsOneWidget);
        expect(find.text('MOBILE NUMBER *'), findsOneWidget);
        expect(find.text('+91'), findsOneWidget);
      });
    }

    testWidgets('10-digit mobile stays inside the phone field on a narrow Android width', (tester) async {
      tester.view.physicalSize = const Size(360, 740);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final dio = Dio();
      dio.httpClientAdapter = _ImmediateAdapter();
      final api = ApiClient(dio: dio);

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            Provider<ApiClient>.value(value: api),
            ChangeNotifierProvider(create: (_) => AuthProvider(api)),
            ChangeNotifierProvider(create: (_) => BookingFlowProvider()),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WebsiteBookingScreen(embeddedInShell: true),
              bottomNavigationBar: SizedBox(height: _nav),
            ),
          ),
        ),
      );
      await tester.pump();

      const number = '9372792693';
      final phone = find.byWidgetPredicate(
        (widget) => widget is TextField && widget.decoration?.hintText == '10 digits',
      );
      expect(phone, findsOneWidget);
      await tester.enterText(phone, number);
      await tester.pump();

      final field = tester.widget<TextField>(phone);
      expect(field.controller?.text, number);
      expect(field.maxLines, 1);
      final style = field.style!;
      expect(style.fontSize!, greaterThanOrEqualTo(13));
      final box = tester.getSize(phone);
      // Android Roboto digits are about 0.6em. The widget-test font is a full
      // em wide, so compare against a device digit, and keep the field scrollable.
      const deviceDigitEm = 0.62;
      const horizontalPad = 12.0;
      expect(
        box.width,
        greaterThanOrEqualTo(style.fontSize! * deviceDigitEm * number.length + horizontalPad),
        reason: 'field=${box.width} font=${style.fontSize}',
      );
    });
  });
}

class _ImmediateAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      '{"detail":"offline"}',
      500,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
