import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pest_99_partner_app/core/api_client.dart';
import 'package:pest_99_partner_app/core/notification_navigation.dart';
import 'package:pest_99_partner_app/core/notification_open_plan.dart';
import 'package:pest_99_partner_app/core/routing/app_router.dart';
import 'package:pest_99_partner_app/features/bookings/bookings_screen.dart';
import 'package:pest_99_partner_app/models/booking.dart';
import 'package:pest_99_partner_app/providers/bookings_provider.dart';
import 'package:pest_99_partner_app/providers/profile_provider.dart';
import 'package:pest_99_partner_app/services/booking_service.dart';
import 'package:pest_99_partner_app/services/profile_service.dart';
import 'package:pest_99_partner_app/shared/widgets/booking_day_sections.dart';
import 'package:provider/provider.dart';

/// 30 Sep 2026 13:00 IST. On 28 Sep 2026 this is Later.
const _job3860Schedule = '2026-09-30T07:30:00Z';

PartnerBooking _job(int id, String schedule) => PartnerBooking(
      id: id,
      serviceType: 'Cockroach Standard',
      scheduleDatetime: schedule,
      timeSlot: '01:00 PM',
      price: '1600.00',
      localityName: 'Vikhroli East',
      cityName: 'Mumbai',
    );

class _OfflineAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    return Future.error(
      DioException(
        requestOptions: options,
        type: DioExceptionType.connectionError,
        message: 'offline',
      ),
    );
  }

  @override
  void close({bool force = false}) {}
}

Future<BookingsProvider> _pumpBookings(
  WidgetTester tester, {
  required List<PartnerBooking> jobs,
  Size size = const Size(400, 800),
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final dio = Dio(BaseOptions(baseUrl: 'https://invalid.local'));
  dio.httpClientAdapter = _OfflineAdapter();
  final api = ApiClient(dio: dio);
  final bookings = BookingsProvider(BookingService(api));
  bookings.available = jobs;

  await tester.pumpWidget(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<BookingsProvider>.value(value: bookings),
        ChangeNotifierProvider(
          create: (_) => ProfileProvider(ProfileService(api)),
        ),
      ],
      child: const MaterialApp(home: BookingsScreen()),
    ),
  );
  await tester.pump();
  return bookings;
}

void main() {
  final screenshotNow = DateTime.utc(2026, 9, 28, 9, 58);

  test('3860 on 28 Sep IST is Later before the screen buckets it', () {
    final sections = BookingDaySections.from(
      [_job(3860, _job3860Schedule)],
      now: screenshotNow,
    );
    expect(sections.today, isEmpty);
    expect(sections.tomorrow, isEmpty);
    expect(sections.later.map((b) => b.id), [3860]);
  });

  testWidgets('Tomorrow tap changes the empty copy and a rebuild keeps it', (tester) async {
    final bookings = await _pumpBookings(
      tester,
      jobs: [_job(3860, _job3860Schedule)],
    );

    expect(find.text('No bookings for today'), findsOneWidget);
    expect(find.text('Today (0)'), findsOneWidget);
    expect(find.text('Tomorrow (0)'), findsOneWidget);

    await tester.tap(find.text('Tomorrow (0)'));
    await tester.pump();

    expect(find.text('No bookings for tomorrow'), findsOneWidget);
    expect(find.text('No bookings for today'), findsNothing);

    bookings.notifyListeners();
    await tester.pump();
    expect(find.text('No bookings for tomorrow'), findsOneWidget);

    // A later-date notification must not force the Today tab back.
    bookings.showNotificationBooking(id: 3860, dayTab: null, scrollToCard: false);
    await tester.pump();
    expect(find.text('No bookings for tomorrow'), findsOneWidget);
  });

  testWidgets('empty Today is a short line and Later keeps Accept and Reject', (tester) async {
    await _pumpBookings(
      tester,
      jobs: [_job(3860, _job3860Schedule)],
    );

    final empty = tester.widget<Padding>(find.byKey(const Key('single-day-empty')));
    expect(empty.padding, const EdgeInsets.only(top: 2, bottom: 2));
    expect(find.text('#3860'), findsOneWidget);
    expect(find.text('Wed, 30 Sep'), findsOneWidget);
    expect(find.text('Accept Job'), findsOneWidget);
    expect(find.text('Reject'), findsOneWidget);
  });

  testWidgets('a later job below the fold is scrolled into view', (tester) async {
    final jobs = [
      for (var id = 1; id <= 12; id++)
        _job(id, '2030-07-${id.toString().padLeft(2, '0')}T07:30:00Z'),
      _job(3860, _job3860Schedule),
    ];
    final bookings = await _pumpBookings(
      tester,
      jobs: jobs,
      size: const Size(400, 520),
    );

    expect(find.text('#3860'), findsNothing);

    bookings.showNotificationBooking(id: 3860, dayTab: null, scrollToCard: true);
    for (var i = 0; i < 40; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    expect(find.text('#3860'), findsOneWidget);
    final top = tester.getTopLeft(find.text('#3860')).dy;
    expect(top, greaterThan(-40));
    expect(top, lessThan(520));
  });

  testWidgets('notification tap opens the booking and stays off the empty Today list', (tester) async {
    tester.view.physicalSize = const Size(400, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final dio = Dio(BaseOptions(baseUrl: 'https://invalid.local'));
    dio.httpClientAdapter = _OfflineAdapter();
    final api = ApiClient(dio: dio);
    final bookings = BookingsProvider(BookingService(api));
    final jobs = [
      for (var id = 1; id <= 8; id++)
        _job(id, '2030-08-${id.toString().padLeft(2, '0')}T07:30:00Z'),
      _job(3860, _job3860Schedule),
    ];
    bookings.available = jobs;

    final router = GoRouter(
      navigatorKey: rootNavigatorKey,
      initialLocation: '/splash',
      routes: [
        GoRoute(
          path: '/splash',
          builder: (_, _) => const Scaffold(body: Text('splash')),
        ),
        GoRoute(
          path: '/login',
          builder: (_, _) => const Scaffold(body: Text('login')),
        ),
        StatefulShellRoute.indexedStack(
          builder: (_, _, shell) => shell,
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/bookings',
                  builder: (_, _) => const BookingsScreen(),
                ),
              ],
            ),
          ],
        ),
        GoRoute(
          path: '/booking/:id',
          parentNavigatorKey: rootNavigatorKey,
          builder: (_, state) => Scaffold(
            body: Text('detail ${state.pathParameters['id']}'),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<BookingsProvider>.value(value: bookings),
          ChangeNotifierProvider(
            create: (_) => ProfileProvider(ProfileService(api)),
          ),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pump();

    final data = <String, dynamic>{
      'type': 'new_booking',
      'booking_id': '3860',
      'schedule_datetime': _job3860Schedule,
    };

    // Cold start while splash is up: do not push, or go('/bookings') drops it.
    expect(canPushBookingDetail(router.state.uri.path), isFalse);
    var held = false;
    void open(int id, Map<String, dynamic> payload) {
      if (!canPushBookingDetail(router.state.uri.path)) {
        held = true;
        return;
      }
      held = false;
      NotificationNavigation.openBookingFromPush(id, router: router, data: payload);
    }

    open(3860, data);
    await tester.pump();
    expect(held, isTrue);
    expect(router.state.uri.path, '/splash');
    expect(find.text('detail 3860'), findsNothing);

    // Splash lands on New Bookings, then the queued tap opens the job.
    router.go('/bookings');
    await tester.pump();
    open(3860, data);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 50));

    expect(router.state.uri.path, '/booking/3860');
    expect(find.text('detail 3860').hitTestable(), findsOneWidget);
    // The empty Today list stays mounted under the detail route. The tap
    // must not replace that route with it.
    expect(find.text('No bookings for today').hitTestable(), findsNothing);

    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(router.state.uri.path, '/booking/3860');

    router.pop();
    for (var i = 0; i < 30; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(find.text('#3860'), findsOneWidget);
    final top = tester.getTopLeft(find.text('#3860')).dy;
    expect(top, greaterThan(-40));
    expect(top, lessThan(700));

    // Foreground tap from the list opens the same booking again.
    open(3860, data);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 50));
    expect(router.state.uri.path, '/booking/3860');
    expect(find.text('detail 3860').hitTestable(), findsOneWidget);
    expect(find.text('No bookings for today').hitTestable(), findsNothing);
  });
}
