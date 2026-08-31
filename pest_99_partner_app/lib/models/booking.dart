class PartnerBooking {
  PartnerBooking({
    required this.id,
    this.code,
    required this.serviceType,
    this.serviceCategory,
    this.bookingType,
    this.planLabel,
    this.totalBookingAmount,
    this.clientName,
    this.clientMobile,
    this.clientAddress,
    this.locationDisplay,
    this.cityName,
    this.localityName,
    this.scheduleDatetime,
    this.timeSlot,
    this.status,
    this.partnerStatus,
    this.price,
    this.priceDisplay,
    this.paymentStatus,
    this.paymentMode,
    this.paymentModel,
    this.visitPayoutAmount,
    this.payoutStatus,
    this.technicianSharePercent,
    this.companySharePercent,
    this.visitRevenueAmount,
    this.companyShareAmount,
    this.bookingTag,
    this.canViewClientPhone = false,
    this.canStartJob = false,
    this.canCompleteJob = false,
    this.jobStartSelfieUrl,
    this.startedAt,
    this.completedAt,
    this.notes,
  });

  final int id;
  final String? code;
  final String serviceType;
  final String? serviceCategory;
  final String? bookingType;
  final String? planLabel;
  final String? totalBookingAmount;
  final String? clientName;
  final String? clientMobile;
  final String? clientAddress;
  final String? locationDisplay;
  final String? cityName;
  final String? localityName;
  final String? scheduleDatetime;
  final String? timeSlot;
  final String? status;
  final String? partnerStatus;
  final String? price;
  final String? priceDisplay;
  final String? paymentStatus;
  final String? paymentMode;
  final String? paymentModel;
  final String? visitPayoutAmount;
  final String? payoutStatus;
  final String? technicianSharePercent;
  final String? companySharePercent;
  final String? visitRevenueAmount;
  final String? companyShareAmount;
  final String? bookingTag;
  final bool canViewClientPhone;
  final bool canStartJob;
  final bool canCompleteJob;
  final String? jobStartSelfieUrl;
  final String? startedAt;
  final String? completedAt;
  final String? notes;

  /// Pool booking sent from CRM — partner can accept from app.
  bool get allowsAccept {
    final ps = partnerStatus?.toLowerCase();
    return ps == 'pending' || ps == null || ps.isEmpty;
  }

  /// True when partner can start (accepted, not yet in service).
  bool get allowsStart => canStartJob || partnerStatus == 'accepted';

  /// True when partner can complete (in service).
  bool get allowsComplete => canCompleteJob || partnerStatus == 'in_service';

  bool get hasRevenuePayout {
    final amt = visitPayoutAmount;
    if (amt == null || amt.isEmpty || amt == '0' || amt == '0.00') return false;
    return paymentModel == 'revenue_sharing' ||
        payoutStatus == 'pending' ||
        payoutStatus == 'approved' ||
        payoutStatus == 'paid' ||
        payoutStatus == 'held';
  }

  String get yourShareLabel {
    final pct = technicianSharePercent?.trim();
    if (pct != null && pct.isNotEmpty && pct != '0' && pct != '0.00') {
      final clean = pct.endsWith('.00') ? pct.substring(0, pct.length - 3) : pct;
      return 'Your share ($clean%)';
    }
    return 'Your share (40%)';
  }

  String get companyShareLabel {
    final pct = companySharePercent?.trim();
    if (pct != null && pct.isNotEmpty && pct != '0' && pct != '0.00') {
      final clean = pct.endsWith('.00') ? pct.substring(0, pct.length - 3) : pct;
      return 'Company share ($clean%)';
    }
    return 'Company share (60%)';
  }

  factory PartnerBooking.fromJson(Map<String, dynamic> json) {
    final partnerStatus = json['partner_status']?.toString();
    final canStart = json['can_start_job'] == true || partnerStatus == 'accepted';
    final canComplete = json['can_complete_job'] == true || partnerStatus == 'in_service';
    final rawId = json['id'];
    final id = rawId is int ? rawId : int.tryParse('$rawId') ?? 0;
    return PartnerBooking(
      id: id,
      code: json['code']?.toString(),
      serviceType: '${json['service_type'] ?? ''}',
      serviceCategory: json['service_category']?.toString(),
      bookingType: json['booking_type']?.toString(),
      planLabel: json['plan_label']?.toString(),
      totalBookingAmount: json['total_booking_amount']?.toString(),
      clientName: json['client_name']?.toString(),
      clientMobile: json['client_mobile']?.toString(),
      clientAddress: json['client_address']?.toString(),
      locationDisplay: json['location_display']?.toString(),
      cityName: json['city_name']?.toString(),
      localityName: json['locality_name']?.toString(),
      scheduleDatetime: json['schedule_datetime']?.toString(),
      timeSlot: json['time_slot']?.toString(),
      status: json['status']?.toString(),
      partnerStatus: partnerStatus,
      price: json['price']?.toString(),
      priceDisplay: json['price_display']?.toString(),
      paymentStatus: json['payment_status']?.toString(),
      paymentMode: json['payment_mode']?.toString(),
      paymentModel: json['payment_model']?.toString(),
      visitPayoutAmount: json['visit_payout_amount']?.toString(),
      payoutStatus: json['payout_status']?.toString(),
      technicianSharePercent: json['technician_share_percent']?.toString(),
      companySharePercent: json['company_share_percent']?.toString(),
      visitRevenueAmount: json['visit_revenue_amount']?.toString(),
      companyShareAmount: json['company_share_amount']?.toString(),
      bookingTag: json['booking_tag']?.toString(),
      canViewClientPhone: json['can_view_client_phone'] == true,
      canStartJob: canStart,
      canCompleteJob: canComplete,
      jobStartSelfieUrl: json['job_start_selfie_url']?.toString(),
      startedAt: json['started_at']?.toString(),
      completedAt: json['completed_at']?.toString(),
      notes: json['notes']?.toString(),
    );
  }
}

class BookingCounts {
  BookingCounts({required this.available, required this.accepted, required this.completed});

  final int available;
  final int accepted;
  final int completed;

  factory BookingCounts.fromJson(Map<String, dynamic> json) => BookingCounts(
        available: json['available'] as int? ?? 0,
        accepted: json['accepted'] as int? ?? 0,
        completed: json['completed'] as int? ?? 0,
      );
}
