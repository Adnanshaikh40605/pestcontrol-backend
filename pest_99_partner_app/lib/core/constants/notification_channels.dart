import 'dart:convert';

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

/// Booking id carried on FCM / local notification data.
int? bookingIdFromNotificationData(Map<dynamic, dynamic>? data) {
  if (data == null) return null;
  for (final key in ['booking_id', 'bookingId']) {
    final id = int.tryParse(data[key]?.toString() ?? '');
    if (id != null && id > 0) return id;
  }
  return null;
}

/// Local notification payloads are JSON maps of string fields.
Map<String, dynamic>? notificationDataFromPayload(String? payload) {
  if (payload == null || payload.isEmpty) return null;
  try {
    final decoded = jsonDecode(payload);
    if (decoded is! Map) return null;
    return decoded.map((key, value) => MapEntry(key.toString(), value));
  } catch (_) {
    return null;
  }
}
