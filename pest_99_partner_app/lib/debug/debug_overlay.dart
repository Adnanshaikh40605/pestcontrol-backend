import 'package:flutter/material.dart';

/// Previously wrapped the app with a floating debug FAB (green bug icon).
/// The FAB was removed from the UI; debug tools remain available via code.
class DebugOverlay extends StatelessWidget {
  const DebugOverlay({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => child;
}
