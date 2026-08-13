import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';

class HomeShell extends StatelessWidget {
  const HomeShell({super.key, required this.shell});

  final StatefulNavigationShell shell;

  static const _branchRoutes = ['/home', '/bookings', '/amc', '/payments', '/account'];

  void _onSelect(BuildContext context, int index) {
    if (index == 0) {
      shell.goBranch(0);
      return;
    }
    final auth = context.read<AuthProvider>();
    if (auth.loggedIn) {
      shell.goBranch(index);
      return;
    }
    auth.setPendingRoute(_branchRoutes[index]);
    context.push('/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: shell,
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: AppColors.surface,
          border: Border(top: BorderSide(color: AppColors.divider)),
        ),
        child: NavigationBar(
          selectedIndex: shell.currentIndex,
          onDestinationSelected: (i) => _onSelect(context, i),
          backgroundColor: AppColors.surface,
          indicatorColor: AppColors.successBg,
          elevation: 0,
          height: 68,
          labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded, color: AppColors.primary),
              label: 'Home',
            ),
            NavigationDestination(
              icon: Icon(Icons.event_note_outlined),
              selectedIcon: Icon(Icons.event_note, color: AppColors.primary),
              label: 'Bookings',
            ),
            NavigationDestination(
              icon: Icon(Icons.workspace_premium_outlined),
              selectedIcon: Icon(Icons.workspace_premium, color: AppColors.primary),
              label: 'AMC',
            ),
            NavigationDestination(
              icon: Icon(Icons.account_balance_wallet_outlined),
              selectedIcon: Icon(Icons.account_balance_wallet, color: AppColors.primary),
              label: 'Payments',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              selectedIcon: Icon(Icons.person_rounded, color: AppColors.primary),
              label: 'Account',
            ),
          ],
        ),
      ),
    );
  }
}
