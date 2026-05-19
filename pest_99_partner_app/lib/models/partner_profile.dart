import '../config/api_config.dart';

class PartnerProfile {
  PartnerProfile({
    required this.id,
    required this.fullName,
    required this.mobile,
    this.profileImageUrl,
    this.role = 'technician',
    this.isActive = true,
    this.isAppApproved = false,
    this.stats,
  });

  final int id;
  final String fullName;
  final String mobile;
  final String? profileImageUrl;
  final String role;
  final bool isActive;
  final bool isAppApproved;
  final PartnerStats? stats;

  factory PartnerProfile.fromJson(Map<String, dynamic> json) {
    return PartnerProfile(
      id: json['id'] as int,
      fullName: (json['full_name'] as String?)?.trim() ?? '',
      mobile: (json['mobile'] as String?)?.trim() ?? '',
      profileImageUrl: _resolveMediaUrl(json['profile_image'] as String?),
      role: (json['role'] as String?) ?? 'technician',
      isActive: json['is_active'] as bool? ?? true,
      isAppApproved: json['is_app_approved'] == true,
    );
  }

  /// GET /api/partner/profile/ wraps partner under `partner` key.
  factory PartnerProfile.fromProfileResponse(Map<String, dynamic> data) {
    final partner = data['partner'];
    if (partner is! Map<String, dynamic>) {
      throw FormatException('Missing partner object in profile response');
    }
    final profile = PartnerProfile.fromJson(partner);
    final statsRaw = data['stats'];
    if (statsRaw is Map<String, dynamic>) {
      return PartnerProfile(
        id: profile.id,
        fullName: profile.fullName,
        mobile: profile.mobile,
        profileImageUrl: profile.profileImageUrl,
        role: profile.role,
        isActive: profile.isActive,
        isAppApproved: data['is_app_approved'] == true || profile.isAppApproved,
        stats: PartnerStats.fromJson(statsRaw),
      );
    }
    return profile;
  }

  static String? _resolveMediaUrl(String? path) {
    if (path == null || path.isEmpty) return null;
    if (path.startsWith('http')) return path;
    final base = ApiConfig.baseUrl.replaceAll(RegExp(r'/$'), '');
    final p = path.startsWith('/') ? path : '/$path';
    return '$base$p';
  }
}

class PartnerStats {
  PartnerStats({
    this.totalJobs = 0,
    this.completedJobs = 0,
    this.acceptedJobs = 0,
    this.availableJobs = 0,
    this.serviceCalls = 0,
    this.avgRating = 0,
    this.totalEarnings = '0',
  });

  final int totalJobs;
  final int completedJobs;
  final int acceptedJobs;
  final int availableJobs;
  final int serviceCalls;
  final double avgRating;
  final String totalEarnings;

  factory PartnerStats.fromJson(Map<String, dynamic> json) {
    return PartnerStats(
      totalJobs: json['total_jobs'] as int? ?? 0,
      completedJobs: json['completed_jobs'] as int? ?? 0,
      acceptedJobs: json['accepted_jobs'] as int? ?? 0,
      availableJobs: json['available_jobs'] as int? ?? 0,
      serviceCalls: json['service_calls'] as int? ?? 0,
      avgRating: (json['avg_rating'] is num) ? (json['avg_rating'] as num).toDouble() : 0,
      totalEarnings: '${json['total_earnings'] ?? '0'}',
    );
  }
}
