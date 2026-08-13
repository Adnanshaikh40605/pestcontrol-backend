import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/app_router.dart';
import 'core/theme/app_theme.dart';
import 'providers/auth_provider.dart';
import 'providers/booking_flow_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiClient();
  final auth = AuthProvider(api);
  await auth.bootstrap();
  final appRouter = AppRouter(auth);
  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
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
