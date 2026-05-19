import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';

import 'debug_config.dart';
import 'debug_log_store.dart';
import 'debug_models.dart';

class DebugNetworkService {
  DebugNetworkService._();
  static final DebugNetworkService instance = DebugNetworkService._();

  StreamSubscription<List<ConnectivityResult>>? _sub;

  void start() {
    if (!DebugConfig.enabled) return;
    _sub?.cancel();
    _refresh();
    _sub = Connectivity().onConnectivityChanged.listen((_) => _refresh());
  }

  void stop() {
    _sub?.cancel();
    _sub = null;
  }

  Future<void> _refresh() async {
    if (!DebugConfig.enabled) return;
    try {
      final results = await Connectivity().checkConnectivity();
      final connected = results.any((r) => r != ConnectivityResult.none);
      final label = results.map((r) => r.name).join(', ');
      DebugLogStore.instance.setNetwork(
        NetworkStatusInfo(
          isConnected: connected,
          label: label.isEmpty ? 'none' : label,
          lastChecked: DateTime.now(),
        ),
      );
      if (!connected) {
        DebugLogStore.instance.logWarning(
          'No internet connection',
          message: 'Device appears offline',
        );
      }
    } catch (e) {
      DebugLogStore.instance.setNetwork(
        NetworkStatusInfo(
          isConnected: false,
          label: 'Check failed: $e',
          lastChecked: DateTime.now(),
        ),
      );
    }
  }
}
