import '../config/api_config.dart';
import '../core/api_client.dart';
import '../models/partner_earnings.dart';

class EarningsService {
  EarningsService(this._api);

  final ApiClient _api;

  Future<EarningsHistory> getEarnings() async {
    final data = await _api.get(ApiConfig.earnings);
    return EarningsHistory.fromJson(data);
  }

  Future<List<PartnerSettlement>> getSettlements() async {
    final data = await _api.get(ApiConfig.settlements);
    final raw = data['results'];
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(PartnerSettlement.fromJson)
        .toList();
  }

  Future<PartnerPresence> getPresence() async {
    final data = await _api.get(ApiConfig.presence);
    return PartnerPresence.fromJson(data);
  }

  Future<PartnerPresence> setPresence(String status) async {
    final data = await _api.post(
      ApiConfig.presence,
      body: {'presence_status': status},
    );
    return PartnerPresence.fromJson(data);
  }

  Future<List<PartnerLeaveRequest>> listLeaveRequests() async {
    final data = await _api.get(ApiConfig.leaveRequests);
    final raw = data['results'];
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(PartnerLeaveRequest.fromJson)
        .toList();
  }

  Future<PartnerLeaveRequest> createLeaveRequest({
    required String startDate,
    required String endDate,
    String reason = '',
  }) async {
    final data = await _api.post(
      ApiConfig.leaveRequests,
      body: {
        'start_date': startDate,
        'end_date': endDate,
        'reason': reason,
      },
    );
    return PartnerLeaveRequest.fromJson(data);
  }

  Future<PartnerLeaveRequest> cancelLeaveRequest(int id) async {
    final data = await _api.post(ApiConfig.leaveRequestCancel(id));
    return PartnerLeaveRequest.fromJson(data);
  }
}
