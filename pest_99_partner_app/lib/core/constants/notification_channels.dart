import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Android raw resource name (res/raw/uber_driver_sound.mp3) — no extension.
const String kNewBookingSoundResource = 'uber_driver_sound';

const AndroidNotificationSound kNewBookingNotificationSound =
    RawResourceAndroidNotificationSound(kNewBookingSoundResource);

/// New incoming booking — custom Uber-style alert sound.
const String kNewBookingChannelId = 'pest99_new_booking';
const String kNewBookingChannelName = 'New booking alerts';

/// Other booking updates (assigned, cancelled) — default system sound.
const String kBookingUpdatesChannelId = 'pest99_bookings';
const String kBookingUpdatesChannelName = 'Booking updates';

const String kSystemChannelId = 'pest99_system';
const String kSystemChannelName = 'System';

/// FCM data[type] for pool / send-to-app new booking pushes.
const String kNotificationTypeNewBooking = 'new_booking';

bool isNewBookingPush(Map<String, dynamic> data) {
  final type = data['type']?.toString().toLowerCase() ?? '';
  return type == kNotificationTypeNewBooking;
}
