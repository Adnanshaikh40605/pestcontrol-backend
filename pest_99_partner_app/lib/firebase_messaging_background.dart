import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'core/constants/notification_channels.dart';
import 'firebase_options.dart';
import 'services/partner_local_notifications.dart';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  final data = message.data;
  final isNewBooking = isNewBookingPush(data);
  final title =
      message.notification?.title ?? data['title']?.toString() ?? 'New Booking Available';
  final body = message.notification?.body ?? data['body']?.toString() ?? '';
  final bookingId = int.tryParse(data['booking_id']?.toString() ?? '') ?? message.hashCode;

  await showPartnerLocalNotification(
    id: bookingId,
    title: title,
    body: body,
    data: data,
    isNewBooking: isNewBooking,
  );
}
