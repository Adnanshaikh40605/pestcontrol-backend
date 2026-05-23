import 'dart:convert';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../core/constants/notification_channels.dart';

final FlutterLocalNotificationsPlugin partnerLocalNotifications =
    FlutterLocalNotificationsPlugin();

bool _channelsReady = false;

Future<void> ensurePartnerNotificationChannels() async {
  if (_channelsReady) return;

  const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
  await partnerLocalNotifications.initialize(const InitializationSettings(android: androidInit));

  final androidPlugin = partnerLocalNotifications
      .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();

  await androidPlugin?.createNotificationChannel(
    const AndroidNotificationChannel(
      kNewBookingChannelId,
      kNewBookingChannelName,
      description: 'New bookings from CRM',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
    ),
  );
  await androidPlugin?.createNotificationChannel(
    const AndroidNotificationChannel(
      kBookingUpdatesChannelId,
      kBookingUpdatesChannelName,
      description: 'Assigned, cancelled, and other booking updates',
      importance: Importance.high,
      playSound: true,
    ),
  );

  _channelsReady = true;
}

Future<void> showPartnerLocalNotification({
  required int id,
  required String title,
  required String body,
  required Map<String, dynamic> data,
  required bool isNewBooking,
}) async {
  await ensurePartnerNotificationChannels();

  final channelId = isNewBooking ? kNewBookingChannelId : kBookingUpdatesChannelId;
  final channelName = isNewBooking ? kNewBookingChannelName : kBookingUpdatesChannelName;

  final details = AndroidNotificationDetails(
    channelId,
    channelName,
    channelDescription: isNewBooking ? 'New booking alerts' : 'Booking updates',
    importance: isNewBooking ? Importance.max : Importance.high,
    priority: isNewBooking ? Priority.max : Priority.high,
    icon: '@mipmap/ic_launcher',
    playSound: true,
    enableVibration: true,
    visibility: NotificationVisibility.public,
    tag: 'booking_$id',
  );

  await partnerLocalNotifications.show(
    id,
    title,
    body,
    NotificationDetails(android: details),
    payload: jsonEncode(data),
  );
}
