import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/auth_provider.dart';
import '../../providers/notifications_provider.dart';

enum AppNavTab { bookings, accepted, completed, profile }

extension AppNavTabX on AppNavTab {
  String get routePath => switch (this) {
        AppNavTab.bookings => '/bookings',
        AppNavTab.accepted => '/accepted',
        AppNavTab.completed => '/completed',
        AppNavTab.profile => '/profile',
      };
}

AppNavTab appNavTabFromLocation(String location) {
  if (location.startsWith('/accepted')) return AppNavTab.accepted;
  if (location.startsWith('/completed')) return AppNavTab.completed;
  if (location.startsWith('/profile')) return AppNavTab.profile;
  return AppNavTab.bookings;
}

class AppBottomNav extends StatelessWidget {
  const AppBottomNav({super.key, required this.current});

  final AppNavTab current;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.border)),
        boxShadow: [
          BoxShadow(
            color: Color(0x08000000),
            blurRadius: 8,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _NavItem(
                icon: Icons.calendar_today_outlined,
                selectedIcon: Icons.calendar_today,
                label: 'Bookings',
                selected: current == AppNavTab.bookings,
                onTap: () => _go(context, AppNavTab.bookings),
              ),
              _NavItem(
                icon: Icons.assignment_turned_in_outlined,
                selectedIcon: Icons.assignment_turned_in,
                label: 'Accepted',
                selected: current == AppNavTab.accepted,
                onTap: () => _go(context, AppNavTab.accepted),
              ),
              _NavItem(
                icon: Icons.verified_outlined,
                selectedIcon: Icons.verified,
                label: 'Completed',
                selected: current == AppNavTab.completed,
                onTap: () => _go(context, AppNavTab.completed),
              ),
              _NavItem(
                icon: Icons.person_outline,
                selectedIcon: Icons.person,
                label: 'Profile',
                selected: current == AppNavTab.profile,
                onTap: () => _go(context, AppNavTab.profile),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _go(BuildContext context, AppNavTab tab) {
    if (tab == current) return;
    context.go(tab.routePath);
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? AppColors.primaryContainer : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              selected ? selectedIcon : icon,
              size: 24,
              color: selected ? AppColors.onPrimary : AppColors.onSurfaceVariant,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: selected ? AppColors.onPrimary : AppColors.onSurfaceVariant,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0,
                    fontSize: 11,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class MainShellScaffold extends StatefulWidget {
  const MainShellScaffold({
    super.key,
    required this.navigationShell,
  });

  final StatefulNavigationShell navigationShell;

  @override
  State<MainShellScaffold> createState() => _MainShellScaffoldState();
}

class _MainShellScaffoldState extends State<MainShellScaffold> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _refreshIfLoggedIn());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _refreshIfLoggedIn();
    }
  }

  Future<void> _refreshIfLoggedIn() async {
    if (!mounted) return;
    final auth = context.read<AuthProvider>();
    if (!auth.loggedIn || !auth.appApproved) return;
    await context.read<NotificationsProvider>().load(force: true);
  }

  @override
  Widget build(BuildContext context) {
    final tab = appNavTabFromLocation(GoRouterState.of(context).uri.path);

    return Scaffold(
      body: widget.navigationShell,
      bottomNavigationBar: AppBottomNav(current: tab),
    );
  }
}
