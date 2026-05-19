import 'dart:convert';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/notification_channels.dart';
import '../debug/debug_log_store.dart';
import '../firebase_messaging_background.dart';
import '../firebase_options.dart';
import 'notification_api_service.dart';

typedef BookingNavigationCallback = void Function(int bookingId);

/// Production FCM + local notifications (foreground, background tap, cold start).
class PushNotificationService {
  PushNotificationService._();
  static final PushNotificationService instance = PushNotificationService._();

  final FlutterLocalNotificationsPlugin _local = FlutterLocalNotificationsPlugin();
  NotificationApiService? _api;
  BookingNavigationCallback? _onOpenBooking;

  String? _cachedToken;
  bool _tokenRefreshListenerAttached = false;
  int? _pendingBookingId;
  int _unreadCount = 0;

  int get unreadCount => _unreadCount;
  final ValueNotifier<int> unreadNotifier = ValueNotifier(0);

  void configure({
    required NotificationApiService api,
    required BookingNavigationCallback onOpenBooking,
  }) {
    _api = api;
    _onOpenBooking = onOpenBooking;
  }

  Future<void> initialize() async {
    await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _local.initialize(
      const InitializationSettings(android: androidInit),
      onDidReceiveNotificationResponse: _onLocalNotificationTap,
    );

    final androidPlugin =
        _local.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    await androidPlugin?.createNotificationChannel(
      const AndroidNotificationChannel(
        kNewBookingChannelId,
        kNewBookingChannelName,
        description: 'New bookings from CRM — custom alert sound',
        importance: Importance.max,
        playSound: true,
        enableVibration: true,
        sound: kNewBookingNotificationSound,
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
      const AndroidNotificationChannel(
        kSystemChannelId,
        kSystemChannelName,
        description: 'Login and account messages',
        importance: Importance.defaultImportance,
      ),
    );

    final messaging = FirebaseMessaging.instance;
    await messaging.setAutoInitEnabled(true);
    await messaging.setForegroundNotificationPresentationOptions(
      alert: false,
      badge: true,
      sound: false,
    );

    FirebaseMessaging.onMessage.listen(_onForegroundMessage);
    FirebaseMessaging.onMessageOpenedApp.listen(_onMessageOpenedApp);

    final initial = await messaging.getInitialMessage();
    if (initial != null) {
      _queueBookingFromPayload(initial.data);
      _log('Cold start notification queued: booking=$_pendingBookingId');
    }

    _log('PushNotificationService initialized');
  }

  /// Call after auth + router are ready (splash / post-login).
  void processPendingNavigation() {
    final id = _pendingBookingId;
    if (id == null) return;
    _pendingBookingId = null;
    if (_onOpenBooking != null) {
      _log('Processing pending navigation → booking $id');
      _onOpenBooking!(id);
    }
  }

  Future<bool> requestPermission() async {
    final settings = await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    final granted = settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
    _log('Notification permission: ${settings.authorizationStatus.name}');
    return granted;
  }

  Future<String?> getToken() async {
    try {
      _cachedToken = await FirebaseMessaging.instance.getToken();
      _log('FCM token: ${_cachedToken != null ? '${_cachedToken!.substring(0, 20)}...' : 'null'}');
      return _cachedToken;
    } catch (e) {
      _log('FCM getToken error: $e');
      return null;
    }
  }

  Future<void> syncTokenWithBackend() async {
    final api = _api;
    if (api == null) return;

    final token = _cachedToken ?? await getToken();
    if (token == null || token.isEmpty) {
      _log('FCM sync skipped — no token');
      return;
    }

    try {
      await api.saveFcmToken(token);
      _log('FCM token synced with backend');
    } catch (e) {
      _log('FCM sync failed: $e');
      rethrow;
    }

    if (!_tokenRefreshListenerAttached) {
      _tokenRefreshListenerAttached = true;
      FirebaseMessaging.instance.onTokenRefresh.listen((newToken) async {
        _cachedToken = newToken;
        _log('FCM token refreshed by Firebase');
        try {
          await api.saveFcmToken(newToken);
          _log('Refreshed token synced');
        } catch (e) {
          _log('Refreshed token sync failed: $e');
        }
      });
    }
  }

  Future<void> showLoginSuccessNotification() async {
    await _showLocal(
      id: 9001,
      channelId: kSystemChannelId,
      channelName: kSystemChannelName,
      title: 'Login Successful',
      body: 'Welcome to Pest 99 Partner',
      useNewBookingSound: false,
    );
  }

  Future<void> removeTokenFromBackend() async {
    final api = _api;
    if (api == null) return;
    try {
      await api.removeFcmToken(_cachedToken);
      _log('FCM token removed from backend');
    } catch (e) {
      _log('FCM remove failed: $e');
    }
    _cachedToken = null;
  }

  void _onForegroundMessage(RemoteMessage message) {
    _log('FCM foreground: ${message.data}');
    final data = message.data;
    final title = message.notification?.title ?? data['title']?.toString() ?? 'Pest 99 Partner';
    final body = message.notification?.body ?? data['body']?.toString() ?? '';
    final bookingId = int.tryParse(data['booking_id']?.toString() ?? '');
    final notifId = bookingId ?? message.hashCode;
    final newBooking = isNewBookingPush(data);

    _showLocal(
      id: notifId,
      channelId: newBooking ? kNewBookingChannelId : kBookingUpdatesChannelId,
      channelName: newBooking ? kNewBookingChannelName : kBookingUpdatesChannelName,
      title: title,
      body: body,
      payload: jsonEncode(data),
      useNewBookingSound: newBooking,
    );
    _bumpUnread();
  }

  void _onMessageOpenedApp(RemoteMessage message) {
    _log('FCM opened from tray: ${message.data}');
    _navigateFromPayload(message.data);
  }

  void _onLocalNotificationTap(NotificationResponse response) {
    if (response.payload == null || response.payload!.isEmpty) return;
    try {
      final data = jsonDecode(response.payload!) as Map<String, dynamic>;
      _navigateFromPayload(data.map((k, v) => MapEntry(k.toString(), v.toString())));
    } catch (e) {
      _log('Invalid notification payload: $e');
    }
  }

  void _queueBookingFromPayload(Map<String, dynamic> data) {
    final bookingId = int.tryParse(data['booking_id']?.toString() ?? '');
    if (bookingId != null) {
      _pendingBookingId = bookingId;
    }
  }

  void _navigateFromPayload(Map<String, dynamic> data) {
    final bookingId = int.tryParse(data['booking_id']?.toString() ?? '');
    if (bookingId == null) return;
    if (_onOpenBooking != null) {
      _onOpenBooking!(bookingId);
    } else {
      _pendingBookingId = bookingId;
    }
  }

  Future<void> _showLocal({
    required int id,
    required String channelId,
    required String channelName,
    required String title,
    required String body,
    String? payload,
    required bool useNewBookingSound,
  }) async {
    final isSystem = channelId == kSystemChannelId;
    final details = AndroidNotificationDetails(
      channelId,
      channelName,
      channelDescription: isSystem
          ? 'System messages'
          : useNewBookingSound
              ? 'New bookings — custom alert'
              : 'Booking updates',
      importance: isSystem
          ? Importance.defaultImportance
          : useNewBookingSound
              ? Importance.max
              : Importance.high,
      priority: isSystem
          ? Priority.defaultPriority
          : useNewBookingSound
              ? Priority.max
              : Priority.high,
      icon: '@mipmap/ic_launcher',
      playSound: true,
      sound: useNewBookingSound ? kNewBookingNotificationSound : null,
      tag: channelId == kSystemChannelId ? 'login' : 'booking_$id',
    );
    await _local.show(
      id,
      title,
      body,
      NotificationDetails(android: details),
      payload: payload,
    );
  }

  void _bumpUnread() {
    _unreadCount++;
    unreadNotifier.value = _unreadCount;
  }

  void setUnreadCount(int count) {
    _unreadCount = count;
    unreadNotifier.value = count;
  }

  void _log(String message) {
    debugPrint('[FCM] $message');
    DebugLogStore.instance.logAuth('FCM', message: message);
  }
}

void navigateToBookingFromNotification(GoRouter router, int bookingId) {
  router.push('/booking/$bookingId');
}
