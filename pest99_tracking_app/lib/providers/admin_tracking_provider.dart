import 'dart:async';

import 'package:flutter/foundation.dart';

import '../services/admin_tracking_service.dart';

class AdminTrackingProvider extends ChangeNotifier {
  AdminTrackingProvider(this._admin);

  final AdminTrackingService _admin;
  Timer? _pollTimer;

  List<Map<String, dynamic>> staff = [];
  bool loading = false;
  String? error;
  DateTime? lastUpdated;

  void startPolling({Duration interval = const Duration(seconds: 30)}) {
    _pollTimer?.cancel();
    refresh();
    _pollTimer = Timer.periodic(interval, (_) => refresh(silent: true));
  }

  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  Future<void> refresh({bool silent = false}) async {
    if (!silent) {
      loading = true;
      notifyListeners();
    }
    try {
      staff = await _admin.getLiveStaff();
      lastUpdated = DateTime.now();
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  int get onDutyCount => staff.where((s) => s['status'] == 'on_duty').length;

  @override
  void dispose() {
    stopPolling();
    super.dispose();
  }
}
