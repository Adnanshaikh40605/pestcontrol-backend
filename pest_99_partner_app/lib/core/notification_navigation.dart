import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../providers/bookings_provider.dart';
import 'constants/notification_channels.dart';
import 'notification_open_plan.dart';
import 'routing/app_router.dart';
import 'routing/booking_open_args.dart';

/// Opens booking detail after FCM / system notification tap with fresh API data.
class NotificationNavigation {
  NotificationNavigation._();

  /// Sync lists when FCM arrives (cancelled / new booking) without full-screen reload.
  static Future<void> handleForegroundPushData(Map<String, dynamic> data) async {
    final ctx = rootNavigatorKey.currentContext;
    if (ctx == null || !ctx.mounted) return;
    final bookings = ctx.read<BookingsProvider>();
    final bookingId = int.tryParse(data['booking_id']?.toString() ?? '');

    if (isBookingCancelledPush(data) && bookingId != null) {
      bookings.removeFromAvailable(bookingId);
      try {
        await bookings.refreshListsLight(force: true);
      } catch (_) {}
      return;
    }

    if (isNewBookingPush(data)) {
      try {
        await bookings.refreshListsLight(force: true);
      } catch (_) {}
    }
  }

  static Future<void> openBookingFromPush(
    int bookingId, {
    required GoRouter router,
    Map<String, dynamic>? data,
  }) async {
    final ctx = rootNavigatorKey.currentContext;
    final openArgs = BookingOpenArgs.fromNotification();
    final plan = NotificationOpenPlan.fromNotificationData(
      data,
      bookingId: bookingId,
    );

    // Select Today/Tomorrow or mark the Later card before any network wait.
    // Awaiting the available list used to leave the technician on an empty
    // Today tab, and a later `go('/bookings')` dropped the detail route.
    if (ctx != null && ctx.mounted && plan != null) {
      ctx.read<BookingsProvider>().showNotificationBooking(
            id: bookingId,
            dayTab: plan.dayTabIndex,
            scrollToCard: plan.scrollToCard,
          );
    }

    if (kDebugMode) {
      debugPrint(
        '[NotificationNavigation] open booking #$bookingId '
        'type=${data?['type']} bucket=${plan?.bucket} path=${plan?.detailPath}',
      );
    }

    _pushDetailWhenReady(router, bookingId, openArgs);

    final revealCtx = ctx;
    if (revealCtx != null && revealCtx.mounted) {
      unawaited(_revealQuietly(revealCtx, bookingId));
    }
  }

  /// Push the booking page once splash/login is gone. `go('/bookings')` is
  /// not used here: it replaces the stack and on a phone it was beating the
  /// detail push, so the tap landed on the empty New Bookings list.
  static void _pushDetailWhenReady(
    GoRouter router,
    int bookingId,
    BookingOpenArgs openArgs,
  ) {
    final path = '/booking/$bookingId';
    var attempts = 0;

    void attempt() {
      if (attempts++ > 45) {
        debugPrint('[NotificationNavigation] gave up opening $path');
        return;
      }
      final current = router.state.uri.path;
      if (!canPushBookingDetail(current)) {
        WidgetsBinding.instance.addPostFrameCallback((_) => attempt());
        return;
      }
      if (current == path) return;
      router.push(path, extra: openArgs);
    }

    WidgetsBinding.instance.addPostFrameCallback((_) => attempt());
  }

  static Future<void> _revealQuietly(BuildContext ctx, int bookingId) async {
    try {
      if (!ctx.mounted) return;
      await ctx.read<BookingsProvider>().revealNotificationBooking(bookingId);
    } catch (e, st) {
      debugPrint('[NotificationNavigation] reveal booking #$bookingId failed: $e\n$st');
    }
  }
}
