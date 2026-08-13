import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../home/home_screen.dart';
import '../visits/visits_screen.dart';
import '../tasks/tasks_screen.dart';
import '../more/more_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0;

  static const _tabs = [
    (icon: Icons.home_rounded, label: 'Today'),
    (icon: Icons.place_rounded, label: 'Visits'),
    (icon: Icons.task_alt_rounded, label: 'Tasks'),
    (icon: Icons.more_horiz_rounded, label: 'More'),
  ];

  static const _screens = [HomeScreen(), VisitsScreen(), TasksScreen(), MoreScreen()];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: IndexedStack(index: _index, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          for (final tab in _tabs)
            NavigationDestination(icon: Icon(tab.icon), label: tab.label),
        ],
      ),
    );
  }
}
