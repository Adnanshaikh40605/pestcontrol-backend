import '../config/api_config.dart';
import '../core/api_client.dart';
import '../models/partner_notification.dart';

class NotificationApiService {
  NotificationApiService(this._api);

  final ApiClient _api;

  Future<void> saveFcmToken(String token, {String deviceType = 'android'}) async {
    await _api.post(
      ApiConfig.saveFcmToken,
      body: {'fcm_token': token, 'device_type': deviceType},
    );
  }

  Future<void> removeFcmToken(String? token) async {
    await _api.post(
      ApiConfig.removeFcmToken,
      body: token != null ? {'fcm_token': token} : {},
    );
  }

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
