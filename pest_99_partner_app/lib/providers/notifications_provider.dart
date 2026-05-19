import 'package:flutter/foundation.dart';

import '../models/partner_notification.dart';
import '../services/notification_api_service.dart';
import '../services/push_notification_service.dart';

class NotificationsProvider extends ChangeNotifier {
  NotificationsProvider(this._api);

  final NotificationApiService _api;

  List<PartnerNotificationItem> items = [];
  bool loading = false;
  String? error;

  Future<void> load({bool force = false}) async {
    if (loading && !force) return;
    loading = true;
    error = null;
    notifyListeners();
    try {
      final res = await _api.fetchNotifications();
      items = res.results;
      PushNotificationService.instance.setUnreadCount(res.unreadCount);
    } catch (e) {
      error = 'Could not load notifications';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> markAllRead() async {
    await _api.markAllRead();
    items = items.map((n) => PartnerNotificationItem(
          id: n.id,
          notificationType: n.notificationType,
          title: n.title,
          body: n.body,
          bookingId: n.bookingId,
          isRead: true,
          createdAt: n.createdAt,
        )).toList();
    PushNotificationService.instance.setUnreadCount(0);
    notifyListeners();
  }
}
