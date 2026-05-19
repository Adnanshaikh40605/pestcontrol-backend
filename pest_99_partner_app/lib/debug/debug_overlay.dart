import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'debug_config.dart';
import 'debug_panel.dart';

/// Draggable floating debug button (debug builds only).
class DebugOverlay extends StatelessWidget {
  const DebugOverlay({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (!DebugConfig.enabled) return child;
    return Stack(
      clipBehavior: Clip.none,
      children: [
        child,
        const _DebugFloatingButton(),
      ],
    );
  }
}

class _DebugFloatingButton extends StatefulWidget {
  const _DebugFloatingButton();

  @override
  State<_DebugFloatingButton> createState() => _DebugFloatingButtonState();
}

class _DebugFloatingButtonState extends State<_DebugFloatingButton> {
  Offset _position = const Offset(16, 120);

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    return Positioned(
      left: _position.dx.clamp(8, size.width - 64),
      top: _position.dy.clamp(80, size.height - 160),
      child: GestureDetector(
        onPanUpdate: (d) {
          setState(() => _position += d.delta);
        },
        onTap: () => DebugPanel.show(context),
        onLongPress: () {
          HapticFeedback.mediumImpact();
          DebugPanel.show(context, initialTab: 1);
        },
        child: Material(
          elevation: 6,
          shadowColor: Colors.black45,
          color: const Color(0xFF1B4332),
          shape: const CircleBorder(),
          child: Container(
            width: 52,
            height: 52,
            alignment: Alignment.center,
            child: const Icon(Icons.bug_report, color: Colors.white, size: 26),
          ),
        ),
      ),
    );
  }
}
