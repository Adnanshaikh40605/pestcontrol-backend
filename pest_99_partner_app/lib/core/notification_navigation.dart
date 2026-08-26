import 'package:flutter/foundation.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../providers/bookings_provider.dart';
import 'constants/notification_channels.dart';
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

    if (ctx != null) {
      try {
        await ctx.read<BookingsProvider>().refreshListsLight();
      } catch (e, st) {
        debugPrint('[NotificationNavigation] list refresh failed: $e\n$st');
      }

      if (!ctx.mounted) {
        _pushBookingRoute(router, bookingId, openArgs);
        return;
      }

      final isNewBooking = data != null && isNewBookingPush(data);
      if (isNewBooking) {
        router.go('/bookings');
        await Future<void>.delayed(const Duration(milliseconds: 80));
      }
    }

    _pushBookingRoute(router, bookingId, openArgs);
  }

  static void _pushBookingRoute(
    GoRouter router,
    int bookingId,
    BookingOpenArgs openArgs,
  ) {
    final path = '/booking/$bookingId';
    final current = router.state.uri.path;
    if (current == path) {
      router.pop();
    }
    router.push(path, extra: openArgs);
  }
}
