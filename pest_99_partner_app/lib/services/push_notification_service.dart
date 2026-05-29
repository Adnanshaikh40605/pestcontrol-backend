import 'dart:async';
import 'dart:convert';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import '../core/constants/notification_channels.dart';
import '../core/notification_navigation.dart';
import '../debug/debug_log_store.dart';
import '../firebase_messaging_background.dart';
import '../firebase_options.dart';
import 'notification_api_service.dart';
import 'partner_local_notifications.dart';

typedef BookingNavigationCallback = void Function(
  int bookingId,
  Map<String, dynamic> data,
);

/// Production FCM + local notifications (foreground, background tap, cold start).
class PushNotificationService {
  PushNotificationService._();
  static final PushNotificationService instance = PushNotificationService._();

  NotificationApiService? _api;
  BookingNavigationCallback? _onOpenBooking;

  String? _cachedToken;
  bool _tokenRefreshListenerAttached = false;
  int? _pendingBookingId;
  Map<String, dynamic> _pendingData = {};
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

    // Single init — do not call initialize() again in channel setup (breaks channels on Android).
    await initializePartnerLocalNotifications(
      onDidReceiveNotificationResponse: _onLocalNotificationTap,
    );
    await requestPartnerNotificationPermission();
    await ensurePartnerNotificationChannels();

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

  /// Ensures Android notification permission before showing local alerts.
  Future<bool> ensureDisplayPermission() async {
    if (await canShowPartnerNotifications()) return true;
    return requestPartnerNotificationPermission();
  }

  /// Call after auth + router are ready (splash / post-login).
  void processPendingNavigation() {
    final id = _pendingBookingId;
    if (id == null) return;
    final data = Map<String, dynamic>.from(_pendingData);
    _pendingBookingId = null;
    _pendingData = {};
    if (_onOpenBooking != null) {
      _log('Processing pending navigation -> booking $id');
      _onOpenBooking!(id, data);
    }
  }

  Future<bool> requestPermission() async {
    await requestPartnerNotificationPermission();
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

    _attachTokenRefreshListener(api);
  }

  /// Call after login / app resume — retries until token is saved on the server.
  Future<bool> ensureTokenSyncedWithBackend({int maxAttempts = 4}) async {
    final api = _api;
    if (api == null) return false;

    await requestPermission();

    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      final token = await getToken();
      if (token == null || token.isEmpty) {
        _log('FCM ensure: no token yet (attempt $attempt/$maxAttempts)');
        await Future<void>.delayed(Duration(seconds: attempt));
        continue;
      }
      try {
        await api.saveFcmToken(token);
        _log('FCM ensure: token saved (attempt $attempt)');
        _attachTokenRefreshListener(api);
        return true;
      } catch (e) {
        _log('FCM ensure failed attempt $attempt: $e');
        await Future<void>.delayed(Duration(seconds: attempt));
      }
    }
    return false;
  }

  void _attachTokenRefreshListener(NotificationApiService api) {
    if (_tokenRefreshListenerAttached) return;
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

  Future<bool> showLoginSuccessNotification() async {
    await ensureDisplayPermission();
    // Brief delay so OEMs don't drop the alert during login screen transition.
    await Future<void>.delayed(const Duration(milliseconds: 400));
    final shown = await showLoginSuccessLocalNotification(
      title: 'Login Successful',
      body: 'Welcome to Pest 99 Partner',
    );
    if (shown) {
      _log('Login success local notification shown');
    } else {
      _log('Login success local notification not shown (permission or system block)');
    }
    return shown;
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

  Future<void> _onForegroundMessage(RemoteMessage message) async {
    _log('FCM foreground: ${message.data}');
    final data = message.data;
    unawaited(NotificationNavigation.handleForegroundPushData(data));
    final title = message.notification?.title ?? data['title']?.toString() ?? 'Pest 99 Partner';
    final body = message.notification?.body ?? data['body']?.toString() ?? '';
    if (body.isEmpty && title == 'Pest 99 Partner') {
      _log('FCM foreground ignored — empty payload');
      return;
    }

    await ensureDisplayPermission();
    final bookingId = int.tryParse(data['booking_id']?.toString() ?? '');
    final notifId = bookingId ?? message.hashCode;
    final newBooking = isNewBookingPush(data);

    try {
      await showPartnerLocalNotification(
        id: notifId,
        title: title,
        body: body,
        data: data,
        isNewBooking: newBooking,
      );
      _bumpUnread();
    } catch (e) {
      _log('FCM foreground local show failed: $e');
    }
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
      _pendingData = Map<String, dynamic>.from(data);
    }
  }

  void _navigateFromPayload(Map<String, dynamic> data) {
    final bookingId = int.tryParse(data['booking_id']?.toString() ?? '');
    if (bookingId == null) return;
    if (_onOpenBooking != null) {
      _onOpenBooking!(bookingId, data);
    } else {
      _pendingBookingId = bookingId;
      _pendingData = Map<String, dynamic>.from(data);
    }
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
