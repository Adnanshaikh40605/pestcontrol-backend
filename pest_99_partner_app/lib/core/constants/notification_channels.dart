/// New booking alerts — custom urgent sound (`booking_alert_urgent.mp3`).
/// Channel id bumped when sound/settings change on installed devices.
const String kNewBookingChannelId = 'pest99_booking_alerts_v7';
const String kNewBookingChannelName = 'New booking alerts';

/// Other booking updates (assigned, cancelled) — default system sound.
const String kBookingUpdatesChannelId = 'pest99_bookings';
const String kBookingUpdatesChannelName = 'Booking updates';

/// Login success — custom sound (`login_success_loud.mp3`).
const String kLoginChannelId = 'pest99_login_v3';
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
