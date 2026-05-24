import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'app_lifecycle.dart';
import 'core/theme/app_theme.dart';
import 'debug/debug_config.dart';
import 'debug/debug_dio_interceptor.dart';
import 'debug/debug_overlay.dart';

class Pest99PartnerApp extends StatelessWidget {
  const Pest99PartnerApp({super.key, required this.router});

  final GoRouter router;

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Pest 99 Partner',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: router,
      builder: (context, child) {
        if (DebugConfig.enabled) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            try {
              debugSyncGoRoute(GoRouter.of(context).state.uri.toString());
            } catch (_) {}
          });
        }
        return DebugOverlay(
          child: PartnerAppLifecycle(child: child ?? const SizedBox.shrink()),
        );
      },
    );
  }
}
