import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';

/// Routes guests can open without logging in.
const Set<String> kGuestAllowedRoutes = {
  '/home',
  '/login',
  '/register',
  '/otp',
  // Browse booking + see CRM prices before signing in.
  '/book/property',
  '/book/datetime',
  '/book/summary',
};

/// If logged in → run [action]. Else save [pendingRoute] and open login.
void requireLogin(
  BuildContext context, {
  required VoidCallback action,
  String? pendingRoute,
}) {
  final auth = context.read<AuthProvider>();
  if (auth.loggedIn) {
    action();
    return;
  }
  auth.setPendingRoute(pendingRoute);
  context.push('/login');
}

/// Push a route, requiring login first when the user is a guest.
void pushAuthed(BuildContext context, String route) {
  requireLogin(
    context,
    pendingRoute: route,
    action: () => context.push(route),
  );
}

/// Go to a shell tab / route, requiring login first when the user is a guest.
void goAuthed(BuildContext context, String route) {
  requireLogin(
    context,
    pendingRoute: route,
    action: () => context.go(route),
  );
}
