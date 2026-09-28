import 'constants/notification_channels.dart';
import 'schedule_day.dart';

/// Where a notification tap should land, computed before any network call.
class NotificationOpenPlan {
  const NotificationOpenPlan({
    required this.bookingId,
    required this.detailPath,
    required this.dayTabIndex,
    required this.scrollToCard,
    required this.bucket,
  });

  final int bookingId;

  /// Always the booking page, including jobs that sit in Later.
  final String detailPath;

  /// 0 = Today, 1 = Tomorrow. Null for Later or an unparsed schedule.
  final int? dayTabIndex;

  /// Scroll the New Bookings list onto this card when it is not on a day tab.
  final bool scrollToCard;
  final String? bucket;

  static NotificationOpenPlan? fromNotificationData(
    Map<dynamic, dynamic>? data, {
    int? bookingId,
    DateTime? now,
  }) {
    final id = bookingId ?? bookingIdFromNotificationData(data);
    if (id == null) return null;
    final bucket = ScheduleDay.bucketFor(
      data?['schedule_datetime']?.toString(),
      now: now,
    );
    final int? dayTab = switch (bucket) {
      'today' => 0,
      'tomorrow' => 1,
      _ => null,
    };
    return NotificationOpenPlan(
      bookingId: id,
      detailPath: '/booking/$id',
      dayTabIndex: dayTab,
      scrollToCard: dayTab == null,
      bucket: bucket,
    );
  }
}

/// Auth screens replace the whole stack, so a detail push there is dropped
/// when splash or login later calls `go('/bookings')`.
const Set<String> bookingNavigationBlockedPaths = {
  '/splash',
  '/login',
  '/register',
  '/registration-success',
  '/pending-approval',
};

bool canPushBookingDetail(String path) =>
    !bookingNavigationBlockedPaths.contains(path);
