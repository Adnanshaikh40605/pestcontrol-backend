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
        'request_type': 'referral',
      },
    );
    final referral = res['referral'] as Map<String, dynamic>?;
    if (referral == null) {
      throw Exception(res['message'] as String? ?? 'Referral failed');
    }
    return PartnerReferral.fromJson(referral);
  }

  /// Technician guest / client inquiry — same CRM pipeline as referrals.
  Future<PartnerReferral> submitGuestRequest({
    required String clientName,
    required String mobile,
    String? area,
    String? serviceType,
    String? preferredDate,
    String? notes,
  }) async {
    final res = await _api.post(
      ApiConfig.guestRequest,
      body: {
        'client_name': clientName,
        'mobile': mobile,
        if (area != null && area.isNotEmpty) 'area': area,
        if (serviceType != null && serviceType.isNotEmpty) 'service_type': serviceType,
        if (preferredDate != null && preferredDate.isNotEmpty)
          'preferred_date': preferredDate,
        if (notes != null && notes.isNotEmpty) 'notes': notes,
        'request_type': 'guest_request',
      },
    );
    final referral = res['referral'] as Map<String, dynamic>?;
    if (referral == null) {
      throw Exception(res['message'] as String? ?? 'Guest request failed');
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
