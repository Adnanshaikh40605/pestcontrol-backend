import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';

import 'core/theme/app_theme.dart';
import 'providers/app_providers.dart';
import 'providers/admin_tracking_provider.dart';
import 'providers/operations_provider.dart';

class Pest99TrackingApp extends StatelessWidget {
  const Pest99TrackingApp({
    super.key,
    required this.auth,
    required this.tracking,
    required this.operations,
    required this.adminTracking,
    required this.router,
  });

  final AuthProvider auth;
  final TrackingProvider tracking;
  final OperationsProvider operations;
  final AdminTrackingProvider adminTracking;
  final GoRouter router;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<TrackingProvider>.value(value: tracking),
        ChangeNotifierProvider<OperationsProvider>.value(value: operations),
        ChangeNotifierProvider<AdminTrackingProvider>.value(value: adminTracking),
      ],
      child: MaterialApp.router(
        title: 'Pest99 Tracking',
        theme: AppTheme.light,
        routerConfig: router,
      ),
    );
  }
}
