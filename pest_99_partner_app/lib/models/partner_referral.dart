class PartnerReferral {
  const PartnerReferral({
    required this.id,
    required this.clientName,
    required this.mobile,
    required this.area,
    required this.status,
    required this.statusLabel,
    this.referredAt,
    this.updatedAt,
  });

  factory PartnerReferral.fromJson(Map<String, dynamic> json) {
    return PartnerReferral(
      id: json['id'] as int,
      clientName: json['client_name'] as String? ?? '',
      mobile: json['mobile'] as String? ?? '',
      area: json['area'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      statusLabel: json['status_label'] as String? ?? 'Pending',
      referredAt: json['referred_at'] != null ? DateTime.tryParse(json['referred_at'] as String) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at'] as String) : null,
    );
  }

  final int id;
  final String clientName;
  final String mobile;
  final String area;
  final String status;
  final String statusLabel;
  final DateTime? referredAt;
  final DateTime? updatedAt;
}
