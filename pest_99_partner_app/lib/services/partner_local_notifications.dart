import 'dart:convert';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../core/constants/notification_channels.dart';
import '../core/constants/notification_sounds.dart';

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
    AndroidNotificationChannel(
      kNewBookingChannelId,
      kNewBookingChannelName,
      description: 'New bookings from CRM — urgent alert',
      importance: Importance.max,
      playSound: true,
      sound: NotificationSounds.bookingAlertUrgent,
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
  await androidPlugin?.createNotificationChannel(
    AndroidNotificationChannel(
      kLoginChannelId,
      kLoginChannelName,
      description: 'Login and account messages',
      importance: Importance.high,
      playSound: true,
      sound: NotificationSounds.loginSuccessLoud,
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
    sound: isNewBooking ? NotificationSounds.bookingAlertUrgent : null,
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

Future<void> showLoginSuccessLocalNotification({
  required String title,
  required String body,
}) async {
  await ensurePartnerNotificationChannels();

  const details = AndroidNotificationDetails(
    kLoginChannelId,
    kLoginChannelName,
    channelDescription: 'Login success',
    importance: Importance.high,
    priority: Priority.high,
    icon: '@mipmap/ic_launcher',
    playSound: true,
    sound: NotificationSounds.loginSuccessLoud,
    tag: 'login_success',
  );

  await partnerLocalNotifications.show(
    9001,
    title,
    body,
    const NotificationDetails(android: details),
  );
}
