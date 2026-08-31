import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/app_update_provider.dart';
import 'providers/auth_provider.dart';
import 'services/push_notification_service.dart';

/// Re-checks Play Store updates + syncs FCM when app returns to foreground.
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

    unawaited(context.read<AppUpdateProvider>().checkForUpdate(silent: true));

    final auth = context.read<AuthProvider>();
    if (!auth.loggedIn || !auth.appApproved) return;
    PushNotificationService.instance.ensureTokenSyncedWithBackend();
    PushNotificationService.instance.processPendingNavigation();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
