import 'package:flutter/material.dart';

import 'app.dart';
import 'core/api_client.dart';
import 'core/routing/app_router.dart';
import 'core/session_coordinator.dart';
import 'providers/app_providers.dart';
import 'providers/admin_tracking_provider.dart';
import 'providers/operations_provider.dart';
import 'services/admin_tracking_service.dart';
import 'services/auth_service.dart';
import 'services/location_service.dart';
import 'services/operations_service.dart';
import 'services/tracking_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  final session = SessionCoordinator();
  final api = ApiClient(sessionCoordinator: session);
  final auth = AuthProvider(AuthService(api), session);
  final tracking = TrackingProvider(TrackingService(api), LocationService());
  final operations = OperationsProvider(OperationsService(api), LocationService());
  final adminTracking = AdminTrackingProvider(AdminTrackingService(api));
  final router = AppRouter(auth).router;

  runApp(Pest99TrackingApp(
    auth: auth,
    tracking: tracking,
    operations: operations,
    adminTracking: adminTracking,
    router: router,
  ));
}
