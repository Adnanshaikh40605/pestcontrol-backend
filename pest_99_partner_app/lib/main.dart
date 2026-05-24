import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'core/api_client.dart';
import 'core/notification_navigation.dart';
import 'core/routing/app_router.dart';
import 'core/session_coordinator.dart';
import 'debug/debug_bootstrap.dart';
import 'debug/debug_log_store.dart';
import 'providers/auth_provider.dart';
import 'providers/bookings_provider.dart';
import 'providers/notifications_provider.dart';
import 'providers/profile_provider.dart';
import 'services/auth_service.dart';
import 'services/booking_service.dart';
import 'services/notification_api_service.dart';
import 'services/profile_service.dart';
import 'services/push_notification_service.dart';

final _routerHolder = _RouterHolder();

Future<void> main() async {
  DebugBootstrap.run(_startApp);
}

Future<void> _startApp() async {
  WidgetsFlutterBinding.ensureInitialized();

  final sessionCoordinator = SessionCoordinator();
  final api = ApiClient(sessionCoordinator: sessionCoordinator);
  final notificationApi = NotificationApiService(api);

  await PushNotificationService.instance.initialize();
  PushNotificationService.instance.configure(
    api: notificationApi,
    onOpenBooking: (id, data) {
      final router = _routerHolder.router;
      if (router != null) {
        NotificationNavigation.openBookingFromPush(
          id,
          router: router,
          data: data,
        );
      }
    },
  );

  final auth = AuthProvider(AuthService(api), sessionCoordinator)..init();

  final appRouter = AppRouter(auth);
  _routerHolder.router = appRouter.router;

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<DebugLogStore>.value(value: DebugLogStore.instance),
        ChangeNotifierProvider(create: (_) => BookingsProvider(BookingService(api))),
        ChangeNotifierProvider(create: (_) => ProfileProvider(ProfileService(api))),
        ChangeNotifierProvider(create: (_) => NotificationsProvider(notificationApi)),
      ],
      child: Pest99PartnerApp(router: appRouter.router),
    ),
  );
}

class _RouterHolder {
  GoRouter? router;
}
