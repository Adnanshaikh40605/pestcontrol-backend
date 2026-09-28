import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pest_99_partner_app/core/notification_navigation.dart';
import 'package:pest_99_partner_app/core/notification_open_plan.dart';

/// Same schedule payload as job 3860. The route under test does not bucket it.
const _laterJob = <String, dynamic>{
  'type': 'new_booking',
  'booking_id': '3860',
  'schedule_datetime': '2026-09-30T07:30:00+00:00',
};

GoRouter _router({required String initial}) {
  return GoRouter(
    initialLocation: initial,
    routes: [
      GoRoute(
        path: '/splash',
        builder: (_, _) => const Scaffold(body: Text('splash')),
      ),
      GoRoute(
        path: '/login',
        builder: (_, _) => const Scaffold(body: Text('login')),
      ),
      GoRoute(
        path: '/bookings',
        builder: (_, _) => const Scaffold(body: Text('bookings')),
      ),
      GoRoute(
        path: '/booking/:id',
        builder: (_, state) => Scaffold(
          body: Text('detail-${state.pathParameters['id']}'),
        ),
      ),
    ],
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('cold start stays on splash until home, then keeps the booking page', (
    tester,
  ) async {
    final router = _router(initial: '/splash');
    addTearDown(router.dispose);
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    expect(router.state.uri.path, '/splash');
    expect(canPushBookingDetail('/splash'), isFalse);

    NotificationNavigation.openBookingFromPush(
      3860,
      router: router,
      data: _laterJob,
    );

    await tester.pump();
    expect(router.state.uri.path, '/splash');
    expect(find.text('detail-3860'), findsNothing);

    // Splash reaches home first. A go() after this push would replace the detail.
    router.go('/bookings');
    await tester.pump();
    await tester.pump();
    await tester.pump();

    expect(router.state.uri.path, '/booking/3860');
    expect(find.text('detail-3860'), findsOneWidget);
    expect(router.canPop(), isTrue);

    await tester.pump(const Duration(milliseconds: 400));
    expect(router.state.uri.path, '/booking/3860');
  });

  testWidgets('foreground tap pushes the booking and does not go back to the list', (
    tester,
  ) async {
    final router = _router(initial: '/bookings');
    addTearDown(router.dispose);
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    expect(canPushBookingDetail('/bookings'), isTrue);

    NotificationNavigation.openBookingFromPush(
      3860,
      router: router,
      data: _laterJob,
    );
    await tester.pumpAndSettle();

    expect(router.state.uri.path, '/booking/3860');
    expect(find.text('detail-3860'), findsOneWidget);
    expect(router.canPop(), isTrue);

    expect(router.state.uri.path, '/booking/3860');
    expect(find.text('bookings').hitTestable(), findsNothing);
  });

  testWidgets('a tap while login is showing waits and still opens the booking', (
    tester,
  ) async {
    final router = _router(initial: '/login');
    addTearDown(router.dispose);
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));

    NotificationNavigation.openBookingFromPush(
      3860,
      router: router,
      data: _laterJob,
    );
    await tester.pump();
    expect(router.state.uri.path, '/login');

    router.go('/bookings');
    await tester.pump();
    await tester.pump();
    await tester.pump();

    expect(router.state.uri.path, '/booking/3860');
    expect(find.text('detail-3860'), findsOneWidget);
    expect(router.canPop(), isTrue);
  });
}
