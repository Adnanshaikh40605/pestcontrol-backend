import '../config/api_config.dart';
import '../core/api_client.dart';
import '../models/partner_referral.dart';

class ReferralService {
  ReferralService(this._api);

  final ApiClient _api;

  Future<PartnerReferral> submitReferral({
    required String clientName,
    required String mobile,
    String? area,
  }) async {
    final res = await _api.post(
      ApiConfig.referClient,
      body: {
        'client_name': clientName,
        'mobile': mobile,
        if (area != null && area.isNotEmpty) 'area': area,
      },
    );
    final referral = res['referral'] as Map<String, dynamic>?;
    if (referral == null) {
      throw Exception(res['message'] as String? ?? 'Referral failed');
    }
    return PartnerReferral.fromJson(referral);
  }

  Future<List<PartnerReferral>> listReferrals() async {
    final res = await _api.get(ApiConfig.referrals);
    final results = res['results'] as List<dynamic>? ?? [];
    return results
        .map((e) => PartnerReferral.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PartnerReferral> getReferral(int id) async {
    final res = await _api.get(ApiConfig.referralDetail(id));
    return PartnerReferral.fromJson(res);
  }
}
