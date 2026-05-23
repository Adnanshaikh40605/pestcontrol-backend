/// New booking alerts ΓÇö default system sound (channel id bumped after mute on device).
const String kNewBookingChannelId = 'pest99_booking_alerts_v4';
const String kNewBookingChannelName = 'New booking alerts';

/// Other booking updates (assigned, cancelled) ΓÇö default system sound.
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
