/// The technician's work status, set by the CRM desk.
///
/// The office owns all three values, so the app only ever reads them; there is
/// no online/offline toggle. `presenceLabel` comes from the server so the
/// wording always matches what CRM staff see.
class PartnerPresence {
  PartnerPresence({
    this.presenceStatus,
    this.presenceLabel = '',
    this.lastActive,
    this.isAvailable = false,
    this.isSuspended = false,
    this.isOnLeave = false,
    this.unavailableReason = '',
    this.suspendReason = '',
    this.technicianLinked = false,
    this.technicianType,
  });

  static const String statusActive = 'active';
  static const String statusOnLeave = 'on_leave';
  static const String statusSuspended = 'suspended';

  final String? presenceStatus;
  final String presenceLabel;
  final String? lastActive;
  final bool isAvailable;
  final bool isSuspended;
  final bool isOnLeave;

  /// Sentence explaining why work is not reaching them; empty when active.
  final String unavailableReason;
  final String suspendReason;
  final bool technicianLinked;
  final String? technicianType;

  bool get isActive => presenceStatus == statusActive;

  /// Either on leave or suspended: no new bookings reach this technician.
  bool get isUnavailable => isSuspended || isOnLeave;

  /// Label to show when the server did not send one (older backend).
  String get displayLabel {
    if (presenceLabel.isNotEmpty) return presenceLabel;
    switch (presenceStatus) {
      case statusOnLeave:
        return 'On Leave';
      case statusSuspended:
        return 'Suspended';
      default:
        return 'Active';
    }
  }

  factory PartnerPresence.fromJson(Map<String, dynamic> json) {
    final status = json['presence_status'] as String?;
    final suspended = json['is_suspended'] == true;
    final onLeave = json['is_on_leave'] == true || status == statusOnLeave;
    return PartnerPresence(
      presenceStatus: status,
      presenceLabel: (json['presence_label'] as String?) ?? '',
      lastActive: json['last_active'] as String?,
      // Older backends omit is_available; derive it so the app never treats a
      // suspended technician as ready for work.
      isAvailable: json['is_available'] == true ||
          (json['is_available'] == null && !suspended && !onLeave),
      isSuspended: suspended,
      isOnLeave: onLeave,
      unavailableReason: (json['unavailable_reason'] as String?) ?? '',
      suspendReason: (json['suspend_reason'] as String?) ?? '',
      technicianLinked: json['technician_linked'] == true,
      technicianType: json['technician_type'] as String?,
    );
  }
}

class PartnerEarning {
  PartnerEarning({
    required this.id,
    this.jobCode,
    this.serviceType,
    required this.amount,
    this.earningType = 'revenue_share',
    this.isApproved = false,
    this.payoutStatus,
    this.visitPayoutAmount,
    this.settlementStatus,
    this.settlementId,
    this.completedAt,
    this.createdAt,
  });

  final int id;
  final String? jobCode;
  final String? serviceType;
  final String amount;
  final String earningType;
  final bool isApproved;
  final String? payoutStatus;
  final String? visitPayoutAmount;
  final String? settlementStatus;
  final int? settlementId;
  final String? completedAt;
  final String? createdAt;

  factory PartnerEarning.fromJson(Map<String, dynamic> json) {
    return PartnerEarning(
      id: json['id'] as int,
      jobCode: json['job_code'] as String?,
      serviceType: json['service_type'] as String?,
      amount: '${json['amount'] ?? '0'}',
      earningType: (json['earning_type'] as String?) ?? 'revenue_share',
      isApproved: json['is_approved'] == true,
      payoutStatus: json['payout_status'] as String?,
      visitPayoutAmount: json['visit_payout_amount']?.toString(),
      settlementStatus: json['settlement_status'] as String?,
      settlementId: json['settlement_id'] as int?,
      completedAt: json['completed_at'] as String?,
      createdAt: json['created_at'] as String?,
    );
  }
}

class EarningsHistory {
  EarningsHistory({
    required this.totalEarnings,
    required this.approvedEarnings,
    required this.results,
  });

  final String totalEarnings;
  final String approvedEarnings;
  final List<PartnerEarning> results;

  factory EarningsHistory.fromJson(Map<String, dynamic> json) {
    final raw = json['results'];
    final list = <PartnerEarning>[];
    if (raw is List) {
      for (final item in raw) {
        if (item is Map<String, dynamic>) {
          list.add(PartnerEarning.fromJson(item));
        }
      }
    }
    return EarningsHistory(
      totalEarnings: '${json['total_earnings'] ?? '0'}',
      approvedEarnings: '${json['approved_earnings'] ?? '0'}',
      results: list,
    );
  }
}

class PartnerLeaveRequest {
  PartnerLeaveRequest({
    required this.id,
    required this.startDate,
    required this.endDate,
    this.reason = '',
    this.status = 'pending',
    this.adminNote = '',
    this.createdAt,
  });

  final int id;
  final String startDate;
  final String endDate;
  final String reason;
  final String status;
  final String adminNote;
  final String? createdAt;

  bool get isPending => status == 'pending';

  factory PartnerLeaveRequest.fromJson(Map<String, dynamic> json) {
    return PartnerLeaveRequest(
      id: json['id'] as int,
      startDate: '${json['start_date'] ?? ''}',
      endDate: '${json['end_date'] ?? ''}',
      reason: (json['reason'] as String?) ?? '',
      status: (json['status'] as String?) ?? 'pending',
      adminNote: (json['admin_note'] as String?) ?? '',
      createdAt: json['created_at'] as String?,
    );
  }
}

class PartnerSettlement {
  PartnerSettlement({
    required this.id,
    required this.periodStart,
    required this.periodEnd,
    this.cadence = 'weekly',
    required this.status,
    this.grossAmount = '0',
    this.incentiveAmount = '0',
    this.deductionAmount = '0',
    this.netAmount = '0',
    this.paidAt,
  });

  final int id;
  final String periodStart;
  final String periodEnd;
  final String cadence;
  final String status;
  final String grossAmount;
  final String incentiveAmount;
  final String deductionAmount;
  final String netAmount;
  final String? paidAt;

  factory PartnerSettlement.fromJson(Map<String, dynamic> json) {
    return PartnerSettlement(
      id: json['id'] as int,
      periodStart: '${json['period_start'] ?? ''}',
      periodEnd: '${json['period_end'] ?? ''}',
      cadence: (json['cadence'] as String?) ?? 'weekly',
      status: (json['status'] as String?) ?? '',
      grossAmount: '${json['gross_amount'] ?? '0'}',
      incentiveAmount: '${json['incentive_amount'] ?? '0'}',
      deductionAmount: '${json['deduction_amount'] ?? '0'}',
      netAmount: '${json['net_amount'] ?? '0'}',
      paidAt: json['paid_at'] as String?,
    );
  }
}
