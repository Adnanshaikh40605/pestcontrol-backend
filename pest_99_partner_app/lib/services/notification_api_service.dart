import '../config/api_config.dart';
import '../core/api_client.dart';
import '../models/partner_notification.dart';

class NotificationApiService {
  NotificationApiService(this._api);

  final ApiClient _api;

  Future<PartnerNotificationListResponse> fetchNotifications() async {
    final data = await _api.get(ApiConfig.notifications);
    return PartnerNotificationListResponse.fromJson(data);
  }

  Future<void> markAllRead() async {
    await _api.post(ApiConfig.markAllNotificationsRead);
  }

  Future<void> markRead(int id) async {
    await _api.post(ApiConfig.markNotificationRead(id));
  }
}
