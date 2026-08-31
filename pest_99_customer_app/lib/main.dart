import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_native_splash/flutter_native_splash.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/app_router.dart';
import 'core/theme/app_theme.dart';
import 'providers/app_update_provider.dart';
import 'providers/auth_provider.dart';
import 'providers/booking_flow_provider.dart';
import 'services/app_version_service.dart';
import 'shared/widgets/update_available_host.dart';

Future<void> main() async {
  final widgetsBinding = WidgetsFlutterBinding.ensureInitialized();
  FlutterNativeSplash.preserve(widgetsBinding: widgetsBinding);

  final api = ApiClient();
  final auth = AuthProvider(api);
  final appUpdate = AppUpdateProvider(AppVersionService(api));
  final appRouter = AppRouter(auth, appUpdate);

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<AppUpdateProvider>.value(value: appUpdate),
        ChangeNotifierProvider(create: (_) => BookingFlowProvider()),
      ],
      child: CustomerApp(router: appRouter.router),
    ),
  );
}

class CustomerApp extends StatefulWidget {
  const CustomerApp({super.key, required this.router});

  final GoRouter router;

  @override
  State<CustomerApp> createState() => _CustomerAppState();
}

class _CustomerAppState extends State<CustomerApp> with WidgetsBindingObserver {
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
          widget.router.go('/force-update');
        }
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Pest Control 99',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: widget.router,
      builder: (context, child) {
        return UpdateAvailableHost(
          playStorePackageId: 'com.pestcontrol99.pest_99_customer_app',
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }
}
