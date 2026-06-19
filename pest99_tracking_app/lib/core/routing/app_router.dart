import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../providers/app_providers.dart';
import '../../features/auth/login_screen.dart';
import '../../features/home/home_screen.dart';
import '../../features/splash/splash_screen.dart';

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
      if (onSplash) return null;
      if (!loggedIn && !onLogin) return '/login';
      if (loggedIn && onLogin) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
    ],
  );
}
