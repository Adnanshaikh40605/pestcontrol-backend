import 'package:flutter/foundation.dart';

import '../core/api_exception.dart';
import '../models/partner_profile.dart';
import '../services/profile_service.dart';

class ProfileProvider extends ChangeNotifier {
  ProfileProvider(this._service);

  final ProfileService _service;

  PartnerProfile? _profile;
  bool _loading = false;
  String? _error;

  PartnerProfile? get profile => _profile;
  bool get loading => _loading;
  String? get error => _error;

  String get displayName => _profile?.fullName.isNotEmpty == true
      ? _profile!.fullName
      : 'Partner';

  String? get avatarUrl => _profile?.profileImageUrl;

  Future<void> loadProfile({bool force = false}) async {
    if (_loading) return;
    if (_profile != null && !force) return;

    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final data = await _service.getProfile();
      if (kDebugMode) {
        debugPrint('Profile API: $data');
      }
      _profile = PartnerProfile.fromProfileResponse(data);
      _error = null;
    } on ApiException catch (e) {
      _error = e.message;
    } catch (e) {
      _error = 'Could not load profile.';
      if (kDebugMode) debugPrint('Profile load error: $e');
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<bool> updateProfile({
    required String fullName,
    String? imagePath,
  }) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final data = await _service.updateProfile(
        fullName: fullName.trim(),
        imagePath: imagePath,
      );
      if (kDebugMode) debugPrint('Profile update: $data');

      final partner = data['partner'];
      if (partner is Map<String, dynamic>) {
        _profile = PartnerProfile.fromJson(partner).copyWithStats(_profile?.stats);
      }
      await loadProfile(force: true);
      return true;
    } on ApiException catch (e) {
      _error = e.message;
      return false;
    } catch (e) {
      _error = 'Could not save profile.';
      if (kDebugMode) debugPrint('Profile update error: $e');
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void clear() {
    _profile = null;
    _error = null;
    _loading = false;
    notifyListeners();
  }
}

extension on PartnerProfile {
  PartnerProfile copyWithStats(PartnerStats? stats) {
    return PartnerProfile(
      id: id,
      fullName: fullName,
      mobile: mobile,
      profileImageUrl: profileImageUrl,
      role: role,
      isActive: isActive,
      isAppApproved: isAppApproved,
      stats: stats ?? this.stats,
    );
  }
}
