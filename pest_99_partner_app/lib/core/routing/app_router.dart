import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/accepted/accepted_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/pending_approval_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/booking_detail/booking_detail_screen.dart';
import '../../features/bookings/bookings_screen.dart';
import '../../features/completed/completed_screen.dart';
import '../../features/profile/edit_profile_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/notifications/notifications_screen.dart';
import '../../features/referral/refer_client_screen.dart';
import '../../features/referral/referral_progress_screen.dart';
import '../../features/force_update/force_update_screen.dart';
import '../../features/splash/splash_screen.dart';
import '../../providers/app_update_provider.dart';
import 'booking_open_args.dart';
import '../../debug/debug_config.dart';
import '../../debug/debug_dio_interceptor.dart';
import '../../providers/auth_provider.dart';
import '../../shared/widgets/app_bottom_nav.dart';

final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>();

class AppRouter {
  AppRouter(this._auth, this._appUpdate) {
    router = GoRouter(
      navigatorKey: rootNavigatorKey,
      initialLocation: '/splash',
      refreshListenable: Listenable.merge([_auth, _appUpdate]),
      redirect: _redirect,
      observers: DebugConfig.enabled ? [DebugRouteObserver()] : [],
      routes: [
        GoRoute(
          path: '/splash',
          pageBuilder: (context, state) => _fadePage(state, const SplashScreen()),
        ),
        GoRoute(
          path: '/force-update',
          pageBuilder: (context, state) => const NoTransitionPage(child: ForceUpdateScreen()),
        ),
        GoRoute(
          path: '/login',
          pageBuilder: (context, state) => _slidePage(state, const LoginScreen()),
        ),
        GoRoute(
          path: '/register',
          pageBuilder: (context, state) => _slidePage(state, const RegisterScreen()),
        ),
        GoRoute(
          path: '/pending-approval',
          pageBuilder: (context, state) => _slidePage(state, const PendingApprovalScreen()),
        ),
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) {
            return MainShellScaffold(navigationShell: navigationShell);
          },
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/bookings',
                  pageBuilder: (context, state) => const NoTransitionPage(child: BookingsScreen()),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/accepted',
                  pageBuilder: (context, state) => const NoTransitionPage(child: AcceptedScreen()),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/completed',
                  pageBuilder: (context, state) => const NoTransitionPage(child: CompletedScreen()),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/profile',
                  pageBuilder: (context, state) => const NoTransitionPage(child: ProfileScreen()),
                ),
              ],
            ),
          ],
        ),
        GoRoute(
          path: '/booking/:id',
          parentNavigatorKey: rootNavigatorKey,
          pageBuilder: (context, state) {
            final id = int.parse(state.pathParameters['id']!);
            final extra = state.extra;
            final openArgs = extra is BookingOpenArgs ? extra : null;
            return _slidePage(
              state,
              BookingDetailScreen(
                key: ValueKey(openArgs?.pageKey(id) ?? 'booking-$id'),
                bookingId: id,
                openArgs: openArgs,
              ),
            );
          },
        ),
        GoRoute(
          path: '/profile/edit',
          parentNavigatorKey: rootNavigatorKey,
          pageBuilder: (context, state) => _slidePage(state, const EditProfileScreen()),
        ),
        GoRoute(
          path: '/notifications',
          parentNavigatorKey: rootNavigatorKey,
          pageBuilder: (context, state) => _slidePage(state, const NotificationsScreen()),
        ),
        GoRoute(
          path: '/refer-client',
          parentNavigatorKey: rootNavigatorKey,
          pageBuilder: (context, state) => _slidePage(state, const ReferClientScreen()),
        ),
        GoRoute(
          path: '/referral-progress',
          parentNavigatorKey: rootNavigatorKey,
          pageBuilder: (context, state) {
            final highlightId = state.extra is int ? state.extra as int : null;
            return _slidePage(
              state,
              ReferralProgressScreen(highlightId: highlightId),
            );
          },
        ),
        GoRoute(
          path: '/referral-success',
          redirect: (_, __) => '/referral-progress',
        ),
      ],
    );
  }

  final AuthProvider _auth;
  final AppUpdateProvider _appUpdate;
  late final GoRouter router;

  String? _redirect(BuildContext context, GoRouterState state) {
    final path = state.matchedLocation;

    if (_appUpdate.forceUpdateRequired) {
      return path == '/force-update' ? null : '/force-update';
    }

    if (!_auth.ready) return null;
    final onAuth = path == '/login' || path == '/register';
    final onSplash = path == '/splash';

    if (!_auth.loggedIn) {
      if (onAuth || onSplash) return null;
      return '/login';
    }
    final onPending = path == '/pending-approval';
    if (!_auth.appApproved) {
      if (onPending || onAuth || onSplash) return null;
      return '/pending-approval';
    }
    if (onAuth || onSplash || onPending) return '/bookings';
    return null;
  }
}

CustomTransitionPage<void> _fadePage(GoRouterState state, Widget child) {
  return CustomTransitionPage(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 300),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      return FadeTransition(opacity: animation, child: child);
    },
  );
}

CustomTransitionPage<void> _slidePage(GoRouterState state, Widget child) {
  return CustomTransitionPage(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 280),
    reverseTransitionDuration: const Duration(milliseconds: 240),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      const begin = Offset(0.04, 0);
      const end = Offset.zero;
      final tween = Tween(begin: begin, end: end).chain(CurveTween(curve: Curves.easeOutCubic));
      return SlideTransition(
        position: animation.drive(tween),
        child: FadeTransition(opacity: animation, child: child),
      );
    },
  );
}
