import '../config/api_config.dart';
import '../core/api_client.dart';

class ProfileService {
  ProfileService(this._api);

  final ApiClient _api;

  Future<Map<String, dynamic>> getProfile() => _api.get(ApiConfig.profile);

  Future<Map<String, dynamic>> updateProfile({
    required String fullName,
    String? imagePath,
  }) async {
    if (imagePath != null && imagePath.isNotEmpty) {
      return _api.putMultipart(
        ApiConfig.profile,
        fields: {'full_name': fullName},
        files: {'profile_image': imagePath},
      );
    }
    return _api.put(
      ApiConfig.profile,
      body: {'full_name': fullName},
    );
  }

  Future<Map<String, dynamic>> referClient({
    required String clientName,
    required String mobile,
    String? area,
  }) =>
      _api.post(
        ApiConfig.referClient,
        body: {
          'client_name': clientName,
          'mobile': mobile,
          if (area != null) 'area': area,
        },
      );
}
