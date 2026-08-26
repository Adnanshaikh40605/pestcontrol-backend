import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/app_router.dart';
import 'core/theme/app_theme.dart';
import 'providers/app_update_provider.dart';
import 'providers/auth_provider.dart';
import 'providers/booking_flow_provider.dart';
import 'services/app_version_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiClient();
  final auth = AuthProvider(api);
  final appUpdate = AppUpdateProvider(AppVersionService(api));
  await Future.wait([
    auth.bootstrap(),
    appUpdate.checkForUpdate(),
  ]);
  final appRouter = AppRouter(auth, appUpdate);
  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<AppUpdateProvider>.value(value: appUpdate),
        ChangeNotifierProvider(create: (_) => BookingFlowProvider()),
      ],
      child: MaterialApp.router(
        title: 'Pest Control 99',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        routerConfig: appRouter.router,
      ),
    ),
  );
}
