import 'package:flutter/material.dart';

import 'booking_flow_screens.dart';

/// Home tab = website-style booking form (marketing dashboard removed).
@Deprecated('Use WebsiteBookingScreen(embeddedInShell: true)')
class HomeDashboardScreen extends StatelessWidget {
  const HomeDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const WebsiteBookingScreen(embeddedInShell: true);
  }
}
