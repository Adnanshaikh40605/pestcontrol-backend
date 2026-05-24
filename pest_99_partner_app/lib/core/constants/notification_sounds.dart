import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Custom sounds in `android/app/src/main/res/raw/` (reference without `.mp3`).
abstract final class NotificationSounds {
  static const bookingAlertUrgent =
      RawResourceAndroidNotificationSound('booking_alert_urgent');
  static const loginSuccessLoud =
      RawResourceAndroidNotificationSound('login_success_loud');
}
