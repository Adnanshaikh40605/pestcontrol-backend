import '../config/api_config.dart';
import '../core/api_client.dart';

class TrackingService {
  TrackingService(this._api);
  final ApiClient _api;

  Future<Map<String, dynamic>> getMe() => _api.get(ApiConfig.me);

  Future<void> recordConsent() => _api.post(ApiConfig.consent);

  Future<Map<String, dynamic>> checkIn({
    required double latitude,
    required double longitude,
    double? accuracyM,
  }) {
    return _api.post(ApiConfig.checkIn, body: {
      'latitude': latitude,
      'longitude': longitude,
      if (accuracyM != null) 'accuracy_m': accuracyM,
    });
  }

  Future<Map<String, dynamic>> checkOut({
    required double latitude,
    required double longitude,
    double? accuracyM,
  }) {
    return _api.post(ApiConfig.checkOut, body: {
      'latitude': latitude,
      'longitude': longitude,
      if (accuracyM != null) 'accuracy_m': accuracyM,
    });
  }

  Future<void> sendPing({
    required double latitude,
    required double longitude,
    double? accuracyM,
    int? batteryPercent,
    bool isMoving = true,
  }) async {
    await _api.post(ApiConfig.locationPing, body: {
      'latitude': latitude,
      'longitude': longitude,
      if (accuracyM != null) 'accuracy_m': accuracyM,
      if (batteryPercent != null) 'battery_percent': batteryPercent,
      'is_moving': isMoving,
      'recorded_at': DateTime.now().toUtc().toIso8601String(),
    });
  }

  Future<void> syncBatch(List<Map<String, dynamic>> pings) async {
    if (pings.isEmpty) return;
    await _api.post(ApiConfig.locationBatch, body: {'pings': pings});
  }
}
