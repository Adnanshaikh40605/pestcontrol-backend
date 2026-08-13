import '../config/api_config.dart';
import '../core/api_client.dart';

class AdminTrackingService {
  AdminTrackingService(this._api);
  final ApiClient _api;

  Future<List<Map<String, dynamic>>> getLiveStaff() async {
    final list = await _api.getList(ApiConfig.liveStaff);
    return list.cast<Map<String, dynamic>>();
  }
}
