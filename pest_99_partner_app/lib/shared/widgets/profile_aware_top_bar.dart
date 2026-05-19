import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/profile_provider.dart';
import 'app_top_bar.dart';

/// Top bar that loads partner profile for avatar/name and navigates to /profile on tap.
class ProfileAwareTopBar extends StatefulWidget implements PreferredSizeWidget {
  const ProfileAwareTopBar({super.key});

  @override
  Size get preferredSize => const AppTopBar().preferredSize;

  @override
  State<ProfileAwareTopBar> createState() => _ProfileAwareTopBarState();
}

class _ProfileAwareTopBarState extends State<ProfileAwareTopBar> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<ProfileProvider>().loadProfile();
    });
  }

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<ProfileProvider>();
    return AppTopBar(
      avatarUrl: profile.avatarUrl,
      avatarLabel: profile.displayName,
    );
  }
}
