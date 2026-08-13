import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../shared/widgets/more_menu_tile.dart';
import '../attendance/attendance_screen.dart';
import '../expenses/expenses_screen.dart';
import '../leave/leave_screen.dart';
import '../profile/profile_screen.dart';

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final items = [
      (Icons.event_note_outlined, 'Attendance History', () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AttendanceScreen()))),
      (Icons.beach_access_outlined, 'Leave', () => Navigator.push(context, MaterialPageRoute(builder: (_) => const LeaveScreen()))),
      (Icons.receipt_long_outlined, 'Expenses', () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ExpensesScreen()))),
      (Icons.person_outline, 'Profile', () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ProfileScreen()))),
    ];

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('More')),
      body: ListView.separated(
        padding: const EdgeInsets.all(AppSpacing.screenEdge),
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, i) {
          final item = items[i];
          return MoreMenuTile(icon: item.$1, title: item.$2, onTap: item.$3);
        },
      ),
    );
  }
}
