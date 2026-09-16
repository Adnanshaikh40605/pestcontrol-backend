import 'package:go_router/go_router.dart';

import '../core/auth_gate.dart';
import '../features/splash/splash_screen.dart';
import '../providers/auth_provider.dart';
import '../screens/account_hub_screens.dart';
import '../screens/booking_detail_screen.dart';
import '../screens/booking_flow_screens.dart';
import '../screens/bookings_screen.dart';
import '../screens/home_dashboard_screen.dart';
import '../screens/home_shell.dart';
import '../screens/invoice_screen.dart';
import '../screens/login_screen.dart';
import '../screens/register_screen.dart';
import '../screens/support_hub_screen.dart';

class AppRouter {
  AppRouter(this._auth) {
    router = GoRouter(
      initialLocation: '/splash',
      refreshListenable: _auth,
      redirect: (context, state) {
        final loc = state.matchedLocation;

        // Splash owns bootstrap + Play Store update check.
        if (loc == '/splash') return null;

        if (!_auth.ready) return '/splash';
        final onAuth = loc == '/login' || loc == '/register' || loc == '/otp';

        // Guests may browse Home + website-style booking; other features need login.
        if (!_auth.loggedIn) {
          if (kGuestAllowedRoutes.contains(loc) || loc.startsWith('/book')) {
            return null;
          }
          return '/login';
        }

        if (_auth.loggedIn && onAuth) {
          // Prefer a real post-auth destination; never loop auth screens.
          final next = _auth.takePendingRoute();
          if (next != null &&
              next.isNotEmpty &&
              next != '/login' &&
              next != '/register' &&
              next != '/otp') {
            return next;
          }
          return '/home';
        }
        return null;
      },
      routes: [
        GoRoute(
          path: '/splash',
          pageBuilder: (_, _) => const NoTransitionPage(child: SplashScreen()),
        ),
        GoRoute(
          path: '/login',
          builder: (_, state) {
            final extra = state.extra;
            String mobile = '';
            if (extra is Map) {
              mobile = '${extra['mobile'] ?? ''}';
            } else if (extra is String) {
              mobile = extra;
            }
            return LoginScreen(initialMobile: mobile);
          },
        ),
        GoRoute(
          path: '/register',
          builder: (_, state) {
            final extra = state.extra;
            String mobile = '';
            if (extra is Map) {
              mobile = '${extra['mobile'] ?? ''}';
            } else if (extra is String) {
              mobile = extra;
            }
            return RegisterScreen(initialMobile: mobile);
          },
        ),
        GoRoute(
          path: '/otp',
          builder: (_, state) {
            final extra = state.extra;
            if (extra is Map) {
              return OtpVerifyScreen(
                mobile: '${extra['mobile'] ?? ''}',
                purpose: '${extra['purpose'] ?? 'login'}',
                fullName: '${extra['fullName'] ?? ''}',
                devOtp: extra['devOtp']?.toString(),
              );
            }
            return OtpVerifyScreen(mobile: '${extra ?? ''}');
          },
        ),
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) => HomeShell(shell: navigationShell),
          branches: [
            StatefulShellBranch(routes: [
              GoRoute(path: '/home', builder: (_, _) => const HomeDashboardScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/bookings', builder: (_, _) => const BookingsScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/support', builder: (_, _) => const SupportHubScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/account', builder: (_, _) => const AccountScreen()),
            ]),
          ],
        ),
        GoRoute(path: '/amc', builder: (_, _) => const AmcDashboardScreen()),
        GoRoute(path: '/payments', builder: (_, _) => const PaymentsScreen()),
        GoRoute(
          path: '/book',
          builder: (_, state) => WebsiteBookingScreen(
            initialServiceId: state.uri.queryParameters['service'],
          ),
        ),
        // Legacy multi-step paths → single website-matched form.
        GoRoute(
          path: '/book/property',
          redirect: (context, state) {
            final service = state.uri.queryParameters['service'];
            return service == null || service.isEmpty
                ? '/book'
                : '/book?service=$service';
          },
        ),
        GoRoute(path: '/book/datetime', redirect: (_, _) => '/book'),
        GoRoute(path: '/book/summary', redirect: (_, _) => '/book'),
        GoRoute(path: '/book/confirmed', builder: (_, _) => const BookingConfirmedScreen()),
        GoRoute(path: '/complaint', builder: (_, _) => const ComplaintScreen()),
        GoRoute(path: '/report', builder: (_, _) => const ServiceReportScreen()),
        GoRoute(
          path: '/amc/:id',
          builder: (_, state) => AmcDetailsScreen(id: state.pathParameters['id']!),
        ),
        GoRoute(path: '/history', builder: (_, _) => const BookingsScreen(historyOnly: true)),
        GoRoute(
          path: '/booking/:id',
          builder: (context, state) {
            final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
            return BookingDetailScreen(bookingId: id);
          },
        ),
        GoRoute(
          path: '/invoice/:id',
          builder: (context, state) {
            final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
            return InvoiceScreen(bookingId: id);
          },
        ),
      ],
    );
  }

  final AuthProvider _auth;
  late final GoRouter router;
}
