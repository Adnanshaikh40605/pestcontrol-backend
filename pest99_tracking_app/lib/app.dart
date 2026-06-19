import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';

import 'providers/app_providers.dart';

class Pest99TrackingApp extends StatelessWidget {
  const Pest99TrackingApp({
    super.key,
    required this.auth,
    required this.tracking,
    required this.router,
  });

  final AuthProvider auth;
  final TrackingProvider tracking;
  final GoRouter router;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<TrackingProvider>.value(value: tracking),
      ],
      child: MaterialApp.router(
        title: 'Pest99 Tracking',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF16A34A)),
          useMaterial3: true,
        ),
        routerConfig: router,
      ),
    );
  }
}
