/// New booking alerts — Mixkit bell (`partner_notification_bell.wav`).
/// Channel id bumped when sound/settings change on installed devices.
const String kNewBookingChannelId = 'pest99_booking_alerts_v8';
const String kNewBookingChannelName = 'New booking alerts';

/// Other booking updates (assigned, cancelled) — same custom bell.
const String kBookingUpdatesChannelId = 'pest99_bookings_v2';
const String kBookingUpdatesChannelName = 'Booking updates';

/// Login success — same Mixkit bell (`partner_notification_bell.wav`).
const String kLoginChannelId = 'pest99_login_v4';
const String kLoginChannelName = 'Login';

/// Legacy id kept for any in-flight references; prefer [kLoginChannelId].
const String kSystemChannelId = kLoginChannelId;
const String kSystemChannelName = kLoginChannelName;

/// FCM data[type] for pool / send-to-app new booking pushes.
const String kNotificationTypeNewBooking = 'new_booking';

const String kNotificationTypeBookingCancelled = 'booking_cancelled';

bool isNewBookingPush(Map<String, dynamic> data) {
  final type = data['type']?.toString().toLowerCase() ?? '';
  return type == kNotificationTypeNewBooking;
}

bool isBookingCancelledPush(Map<String, dynamic> data) {
  final type = data['type']?.toString().toLowerCase() ?? '';
  return type == kNotificationTypeBookingCancelled;
}
