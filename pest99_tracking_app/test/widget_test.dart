import 'package:flutter_test/flutter_test.dart';
import 'package:pest99_tracking_app/app.dart';
import 'package:pest99_tracking_app/core/api_client.dart';
import 'package:pest99_tracking_app/core/routing/app_router.dart';
import 'package:pest99_tracking_app/core/session_coordinator.dart';
import 'package:pest99_tracking_app/providers/app_providers.dart';
import 'package:pest99_tracking_app/services/auth_service.dart';
import 'package:pest99_tracking_app/services/location_service.dart';
import 'package:pest99_tracking_app/services/tracking_service.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    final session = SessionCoordinator();
    final api = ApiClient(sessionCoordinator: session);
    final auth = AuthProvider(AuthService(api), session);
    final tracking = TrackingProvider(TrackingService(api), LocationService());
    final router = AppRouter(auth).router;

    await tester.pumpWidget(
      Pest99TrackingApp(auth: auth, tracking: tracking, router: router),
    );

    expect(find.text('Pest99 Tracking'), findsOneWidget);
  });
}
