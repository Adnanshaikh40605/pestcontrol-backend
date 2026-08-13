import 'package:go_router/go_router.dart';

import '../../providers/app_providers.dart';
import '../../features/auth/login_screen.dart';
import '../../features/shell/main_shell.dart';
import '../../features/splash/splash_screen.dart';
import '../../features/admin/admin_live_screen.dart';

class AppRouter {
  AppRouter(this.auth);

  final AuthProvider auth;

  late final GoRouter router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: auth,
    redirect: (context, state) {
      final loggedIn = auth.isLoggedIn;
      final onLogin = state.matchedLocation == '/login';
      final onSplash = state.matchedLocation == '/splash';
      final isAdmin = auth.isAdminMode;

      if (onSplash) return null;
      if (!loggedIn && !onLogin) return '/login';
      if (loggedIn && onLogin) return isAdmin ? '/admin/live' : '/home';

      if (loggedIn && isAdmin && state.matchedLocation == '/home') {
        return '/admin/live';
      }
      if (loggedIn && !isAdmin && state.matchedLocation.startsWith('/admin')) {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, _) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(path: '/home', builder: (_, _) => const MainShell()),
      GoRoute(path: '/admin/live', builder: (_, _) => const AdminLiveScreen()),
    ],
  );
}
