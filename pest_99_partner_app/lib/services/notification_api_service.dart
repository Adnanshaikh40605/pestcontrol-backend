import '../config/api_config.dart';
import '../core/api_client.dart';

/// Partner FCM token registration with the backend.
/// In-app notification inbox was removed; push delivery still uses these endpoints.
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
}
