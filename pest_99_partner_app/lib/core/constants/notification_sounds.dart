import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Custom sound in `android/app/src/main/res/raw/partner_notification_bell.wav`
/// (reference without extension). Used for booking alerts and login success.
abstract final class NotificationSounds {
  static const partnerBell =
      RawResourceAndroidNotificationSound('partner_notification_bell');

  /// Alias — new booking alerts.
  static const bookingAlertUrgent = partnerBell;

  /// Alias — login success.
  static const loginSuccessLoud = partnerBell;
}
