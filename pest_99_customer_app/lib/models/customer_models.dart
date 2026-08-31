class CustomerProfile {
  CustomerProfile({
    required this.id,
    required this.fullName,
    required this.mobile,
    this.email = '',
    this.clientId,
  });

  final int id;
  final String fullName;
  final String mobile;
  final String email;
  final int? clientId;

  factory CustomerProfile.fromJson(Map<String, dynamic> json) {
    return CustomerProfile(
      id: json['id'] as int,
      fullName: (json['full_name'] as String?) ?? '',
      mobile: (json['mobile'] as String?) ?? '',
      email: (json['email'] as String?) ?? '',
      clientId: json['client_id'] as int?,
    );
  }
}

class CatalogRate {
  CatalogRate({
    required this.id,
    required this.servicePackage,
    required this.planType,
    required this.areaKey,
    required this.amount,
    required this.standardAmount,
    required this.premiumAmount,
    this.regionName,
    this.propertyCategory,
  });

  final int id;
  final String servicePackage;
  final String planType;
  final String areaKey;
  final String amount;
  final String standardAmount;
  final String premiumAmount;
  final String? regionName;
  final String? propertyCategory;

  factory CatalogRate.fromJson(Map<String, dynamic> json) {
    final tiers = json['package_tiers'];
    final standard = tiers is Map ? '${tiers['standard'] ?? json['amount']}' : '${json['amount']}';
    final premium = tiers is Map ? '${tiers['premium'] ?? json['amount']}' : '${json['amount']}';
    return CatalogRate(
      id: json['id'] as int,
      servicePackage: (json['service_package'] as String?) ?? '',
      planType: (json['plan_type'] as String?) ?? '',
      areaKey: (json['area_key'] as String?) ?? '',
      amount: '${json['amount'] ?? '0'}',
      standardAmount: standard,
      premiumAmount: premium,
      regionName: json['region_name'] as String?,
      propertyCategory: json['property_category'] as String?,
    );
  }

  Map<String, dynamic> toBookExtra() => {
        'id': id,
        'service_package': servicePackage,
        'standard': standardAmount,
        'premium': premiumAmount,
        'area_key': areaKey,
        'plan_type': planType,
        'region_name': regionName,
        'property_category': propertyCategory,
      };
}

class CustomerBooking {
  CustomerBooking({
    required this.id,
    this.code,
    required this.serviceType,
    this.status,
    this.paymentStatus,
    this.packageTier,
    this.bookingType,
    this.propertyType,
    this.bhkSize,
    this.price,
    this.invoiceAmount,
    this.clientAddress,
    this.city,
    this.scheduleDatetime,
    this.timeSlot,
    this.notes,
    this.canRate = false,
    this.myRating,
    this.serviceCycle,
    this.maxCycle,
    this.priceConfirmationPending = false,
    this.canCancel = false,
    this.technicianName,
    this.technicianMobile,
    this.technicianPhotoUrl,
    this.partnerStatus,
  });

  final int id;
  final String? code;
  final String serviceType;
  final String? status;
  final String? paymentStatus;
  final String? packageTier;
  final String? bookingType;
  final String? propertyType;
  final String? bhkSize;
  final String? price;
  final String? invoiceAmount;
  final String? clientAddress;
  final String? city;
  final String? scheduleDatetime;
  final String? timeSlot;
  final String? notes;
  final bool canRate;
  final Map<String, dynamic>? myRating;
  final int? serviceCycle;
  final int? maxCycle;
  final bool priceConfirmationPending;
  final bool canCancel;
  final String? technicianName;
  final String? technicianMobile;
  final String? technicianPhotoUrl;
  final String? partnerStatus;

  bool get isDone => (status ?? '').toLowerCase() == 'done';
  bool get isCancelled => (status ?? '').toLowerCase().contains('cancel');
  bool get hasAssignedTechnician {
    final name = (technicianName ?? '').trim();
    return name.isNotEmpty;
  }
  bool get isPaid {
    final raw = (paymentStatus ?? '').trim().toLowerCase();
    // "Unpaid".contains("paid") is true — check exact / prefix carefully.
    if (raw == 'paid') return true;
    if (raw.startsWith('paid')) return true;
    return false;
  }

  /// Customer-facing visit status (hides CRM jargon like Pending / On Process).
  String get visitStatusLabel {
    final s = (status ?? '').trim().toLowerCase();
    if (s.contains('cancel')) return 'Cancelled';
    if (s == 'done' || s == 'completed') return 'Completed';

    final ps = (partnerStatus ?? '').trim().toLowerCase();
    if (ps == 'in_service' || ps.contains('service')) return 'In progress';
    if (ps == 'accepted') return 'Technician assigned';
    if (ps == 'completed') return 'Completed';

    if (s.isEmpty || s == 'pending' || s == 'upcoming') return 'Scheduled';
    if (s.contains('process') || s.contains('accept')) return 'In progress';
    return status!.trim();
  }

  /// Customer-facing payment label.
  String get paymentStatusLabel {
    if (priceConfirmationPending) return 'Price Confirmation Pending';
    if (isPaid) return 'Paid';
    final raw = (paymentStatus ?? '').trim().toLowerCase();
    if (raw.contains('partial')) return 'Partially paid';
    if (raw == 'pending') return 'Unpaid';
    return 'Unpaid';
  }

  /// One-Time / AMC / 2-Service — never show raw CRM booking_type strings.
  String? get planTypeLabel {
    final service = serviceType.toLowerCase();
    if ((maxCycle ?? 0) == 2 && (service.contains('bed') || service.contains('bug'))) {
      return '2-Service Package';
    }
    final bt = (bookingType ?? '').trim().toLowerCase();
    if (bt.isEmpty) return null;
    if (bt.contains('amc')) return 'AMC plan';
    if (bt.contains('one') || bt.contains('new booking')) return 'One-time service';
    if (bt.contains('service call') || bt.contains('follow')) return 'Follow-up visit';
    if (bt.contains('complaint')) return 'Complaint visit';
    return null;
  }

  /// Hide internal app/CRM note dumps from the customer.
  String? get customerNotes {
    final n = (notes ?? '').trim();
    if (n.isEmpty) return null;
    if (n.toLowerCase().startsWith('app booking')) return null;
    return n;
  }

  factory CustomerBooking.fromJson(Map<String, dynamic> json) {
    return CustomerBooking(
      id: json['id'] as int,
      code: json['code'] as String?,
      serviceType: '${json['service_type'] ?? ''}',
      status: json['status'] as String?,
      paymentStatus: json['payment_status'] as String?,
      packageTier: json['package_tier'] as String?,
      bookingType: json['booking_type'] as String?,
      propertyType: json['property_type'] as String?,
      bhkSize: json['bhk_size'] as String?,
      price: json['price']?.toString(),
      invoiceAmount: json['invoice_amount']?.toString(),
      clientAddress: json['client_address'] as String?,
      city: json['city'] as String?,
      scheduleDatetime: json['schedule_datetime'] as String?,
      timeSlot: json['time_slot'] as String?,
      notes: json['notes'] as String?,
      canRate: json['can_rate'] == true,
      myRating: json['my_rating'] is Map<String, dynamic>
          ? json['my_rating'] as Map<String, dynamic>
          : null,
      serviceCycle: json['service_cycle'] is int ? json['service_cycle'] as int : int.tryParse('${json['service_cycle'] ?? ''}'),
      maxCycle: json['max_cycle'] is int ? json['max_cycle'] as int : int.tryParse('${json['max_cycle'] ?? ''}'),
      priceConfirmationPending: json['price_confirmation_pending'] == true ||
          json['is_price_estimated'] == true,
      canCancel: json['can_cancel'] == true,
      technicianName: json['technician_name'] as String?,
      technicianMobile: json['technician_mobile'] as String?,
      technicianPhotoUrl: json['technician_photo_url'] as String?,
      partnerStatus: json['partner_status'] as String?,
    );
  }
}

class AmcScheduleGroup {
  AmcScheduleGroup({required this.parent, required this.visits});

  final CustomerBooking parent;
  final List<CustomerBooking> visits;

  factory AmcScheduleGroup.fromJson(Map<String, dynamic> json) {
    final visitsRaw = json['visits'];
    return AmcScheduleGroup(
      parent: CustomerBooking.fromJson(json['parent'] as Map<String, dynamic>),
      visits: visitsRaw is List
          ? visitsRaw
              .whereType<Map<String, dynamic>>()
              .map(CustomerBooking.fromJson)
              .toList()
          : const [],
    );
  }
}
