import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'providers/app_update_provider.dart';
import 'providers/auth_provider.dart';
import 'services/push_notification_service.dart';

/// Syncs FCM token when app returns to foreground.
class PartnerAppLifecycle extends StatefulWidget {
  const PartnerAppLifecycle({super.key, required this.child});

  final Widget child;

  @override
  State<PartnerAppLifecycle> createState() => _PartnerAppLifecycleState();
}

class _PartnerAppLifecycleState extends State<PartnerAppLifecycle>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) return;

    final appUpdate = context.read<AppUpdateProvider>();
    unawaited(
      appUpdate.checkForUpdate(silent: true).then((_) {
        if (!mounted) return;
        if (appUpdate.forceUpdateRequired) {
          context.go('/force-update');
          return;
        }
        final auth = context.read<AuthProvider>();
        if (!auth.loggedIn || !auth.appApproved) return;
        PushNotificationService.instance.ensureTokenSyncedWithBackend();
        PushNotificationService.instance.processPendingNavigation();
      }),
    );
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
