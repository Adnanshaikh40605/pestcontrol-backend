import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../core/constants/notification_channels.dart';
import '../core/constants/notification_sounds.dart';

final FlutterLocalNotificationsPlugin partnerLocalNotifications =
    FlutterLocalNotificationsPlugin();

bool _pluginInitialized = false;
bool _channelsReady = false;

/// Urgent booking: long vibration pattern (not single pulse).
final Int64List _urgentVibrationPattern = Int64List.fromList([
  0,
  600,
  200,
  600,
  200,
  600,
]);

AndroidFlutterLocalNotificationsPlugin? get _androidPlugin =>
    partnerLocalNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();

Future<void> initializePartnerLocalNotifications({
  DidReceiveNotificationResponseCallback? onDidReceiveNotificationResponse,
}) async {
  if (_pluginInitialized) return;

  await partnerLocalNotifications.initialize(
    const InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    ),
    onDidReceiveNotificationResponse: onDidReceiveNotificationResponse,
  );
  _pluginInitialized = true;
}

Future<void> initializePartnerLocalNotificationsForBackground() async {
  if (_pluginInitialized) return;
  await partnerLocalNotifications.initialize(
    const InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    ),
  );
  _pluginInitialized = true;
}

Future<bool> requestPartnerNotificationPermission() async {
  final android = _androidPlugin;
  if (android == null) return true;
  try {
    final granted = await android.requestNotificationsPermission();
    return granted ?? true;
  } catch (e) {
    debugPrint('[Notifications] permission request failed: $e');
    return false;
  }
}

Future<bool> canShowPartnerNotifications() async {
  final android = _androidPlugin;
  if (android == null) return true;
  try {
    final enabled = await android.areNotificationsEnabled();
    return enabled ?? true;
  } catch (e) {
    debugPrint('[Notifications] areNotificationsEnabled failed: $e');
    return true;
  }
}

Future<void> ensurePartnerNotificationChannels() async {
  if (_channelsReady) return;

  final android = _androidPlugin;
  if (android == null) return;

  await android.createNotificationChannel(
    AndroidNotificationChannel(
      kNewBookingChannelId,
      kNewBookingChannelName,
      description: 'New bookings from CRM — urgent alert with custom sound',
      importance: Importance.max,
      playSound: true,
      sound: NotificationSounds.bookingAlertUrgent,
      audioAttributesUsage: AudioAttributesUsage.alarm,
      enableVibration: true,
      vibrationPattern: _urgentVibrationPattern,
      enableLights: true,
      showBadge: true,
    ),
  );
  await android.createNotificationChannel(
    const AndroidNotificationChannel(
      kBookingUpdatesChannelId,
      kBookingUpdatesChannelName,
      description: 'Assigned, cancelled, and other booking updates',
      importance: Importance.high,
      playSound: true,
      enableVibration: true,
    ),
  );
  await android.createNotificationChannel(
    AndroidNotificationChannel(
      kLoginChannelId,
      kLoginChannelName,
      description: 'Login success with custom sound',
      importance: Importance.max,
      playSound: true,
      sound: NotificationSounds.loginSuccessLoud,
      audioAttributesUsage: AudioAttributesUsage.notification,
      enableVibration: true,
      vibrationPattern: Int64List.fromList([0, 400, 150, 400]),
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

  final withSound = AndroidNotificationDetails(
    channelId,
    channelName,
    channelDescription: isNewBooking ? 'New booking alerts' : 'Booking updates',
    importance: isNewBooking ? Importance.max : Importance.high,
    priority: isNewBooking ? Priority.max : Priority.high,
    icon: '@mipmap/ic_launcher',
    playSound: true,
    sound: isNewBooking ? NotificationSounds.bookingAlertUrgent : null,
    audioAttributesUsage:
        isNewBooking ? AudioAttributesUsage.alarm : AudioAttributesUsage.notification,
    enableVibration: true,
    vibrationPattern: isNewBooking ? _urgentVibrationPattern : null,
    visibility: NotificationVisibility.public,
    category: isNewBooking ? AndroidNotificationCategory.call : null,
    ticker: isNewBooking ? 'New booking' : null,
    tag: 'booking_$id',
  );

  try {
    await partnerLocalNotifications.show(
      id,
      title,
      body,
      NotificationDetails(android: withSound),
      payload: jsonEncode(data),
    );
  } catch (e) {
    debugPrint('[Notifications] show booking failed (custom sound): $e — retrying default sound');
    final fallback = AndroidNotificationDetails(
      channelId,
      channelName,
      channelDescription: isNewBooking ? 'New booking alerts' : 'Booking updates',
      importance: isNewBooking ? Importance.max : Importance.high,
      priority: isNewBooking ? Priority.max : Priority.high,
      icon: '@mipmap/ic_launcher',
      playSound: true,
      enableVibration: true,
      vibrationPattern: isNewBooking ? _urgentVibrationPattern : null,
      visibility: NotificationVisibility.public,
      tag: 'booking_$id',
    );
    await partnerLocalNotifications.show(
      id,
      title,
      body,
      NotificationDetails(android: fallback),
      payload: jsonEncode(data),
    );
  }
}

Future<bool> showLoginSuccessLocalNotification({
  required String title,
  required String body,
}) async {
  await ensurePartnerNotificationChannels();

  var allowed = await canShowPartnerNotifications();
  if (!allowed) {
    allowed = await requestPartnerNotificationPermission();
    if (!allowed) {
      debugPrint('[Notifications] login success skipped — notifications disabled');
      return false;
    }
  }

  final withSound = AndroidNotificationDetails(
    kLoginChannelId,
    kLoginChannelName,
    channelDescription: 'Login success',
    importance: Importance.max,
    priority: Priority.max,
    icon: '@mipmap/ic_launcher',
    playSound: true,
    sound: NotificationSounds.loginSuccessLoud,
    audioAttributesUsage: AudioAttributesUsage.notification,
    enableVibration: true,
    vibrationPattern: Int64List.fromList([0, 400, 150, 400]),
    tag: 'login_success',
  );

  try {
    await partnerLocalNotifications.show(
      9001,
      title,
      body,
      NotificationDetails(android: withSound),
    );
    return true;
  } catch (e) {
    debugPrint('[Notifications] login show failed (custom sound): $e — retrying default sound');
    try {
      final fallback = AndroidNotificationDetails(
        kLoginChannelId,
        kLoginChannelName,
        channelDescription: 'Login success',
        importance: Importance.max,
        priority: Priority.max,
        icon: '@mipmap/ic_launcher',
        playSound: true,
        enableVibration: true,
        vibrationPattern: Int64List.fromList([0, 400, 150, 400]),
        tag: 'login_success',
      );
      await partnerLocalNotifications.show(
        9001,
        title,
        body,
        NotificationDetails(android: fallback),
      );
      return true;
    } catch (e2) {
      debugPrint('[Notifications] login show failed completely: $e2');
      return false;
    }
  }
}
