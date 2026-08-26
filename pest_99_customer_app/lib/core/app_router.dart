import 'package:flutter/foundation.dart' show Listenable;
import 'package:go_router/go_router.dart';

import '../core/auth_gate.dart';
import '../features/force_update/force_update_screen.dart';
import '../providers/app_update_provider.dart';
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

class AppRouter {
  AppRouter(this._auth, this._appUpdate) {
    router = GoRouter(
      initialLocation: '/home',
      refreshListenable: Listenable.merge([_auth, _appUpdate]),
      redirect: (context, state) {
        final loc = state.matchedLocation;

        if (_appUpdate.forceUpdateRequired) {
          return loc == '/force-update' ? null : '/force-update';
        }
        if (loc == '/force-update') {
          return '/home';
        }

        if (!_auth.ready) return null;
        final onAuth = loc == '/login' || loc == '/register' || loc == '/otp';

        // Guests may browse Home; any other feature requires login.
        if (!_auth.loggedIn) {
          if (kGuestAllowedRoutes.contains(loc)) return null;
          return '/login';
        }

        if (_auth.loggedIn && onAuth) {
          final next = _auth.takePendingRoute();
          return next ?? '/home';
        }
        return null;
      },
      routes: [
        GoRoute(
          path: '/force-update',
          builder: (_, _) => ForceUpdateScreen(
            storeUrl: _appUpdate.serverInfo?.storeUrl,
          ),
        ),
        GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
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
              GoRoute(path: '/amc', builder: (_, _) => const AmcDashboardScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/payments', builder: (_, _) => const PaymentsScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/account', builder: (_, _) => const AccountScreen()),
            ]),
          ],
        ),
        GoRoute(path: '/book/property', builder: (_, _) => const PropertySelectionScreen()),
        GoRoute(path: '/book/datetime', builder: (_, _) => const DateTimeSelectionScreen()),
        GoRoute(path: '/book/summary', builder: (_, _) => const BookingSummaryScreen()),
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
  final AppUpdateProvider _appUpdate;
  late final GoRouter router;
}
