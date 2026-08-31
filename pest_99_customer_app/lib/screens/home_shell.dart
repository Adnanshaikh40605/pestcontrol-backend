import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';

class HomeShell extends StatelessWidget {
  const HomeShell({super.key, required this.shell});

  final StatefulNavigationShell shell;

  static const _branchRoutes = ['/home', '/bookings', '/support', '/account'];

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
          boxShadow: [
            BoxShadow(color: Color(0x0D000000), blurRadius: 12, offset: Offset(0, -2)),
          ],
        ),
        child: NavigationBar(
          selectedIndex: shell.currentIndex.clamp(0, 3),
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
              icon: Icon(Icons.headset_mic_outlined),
              selectedIcon: Icon(Icons.headset_mic_rounded, color: AppColors.primary),
              label: 'Support',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              selectedIcon: Icon(Icons.person_rounded, color: AppColors.primary),
              label: 'Profile',
            ),
          ],
        ),
      ),
    );
  }
}
