import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({
    super.key,
    required this.label,
    required this.color,
    this.icon,
    this.pulse = false,
  });

  final String label;
  final Color color;
  final IconData? icon;
  final bool pulse;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: [
          if (pulse)
            Container(
              width: 10,
              height: 10,
              margin: const EdgeInsets.only(right: 8),
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            )
          else if (icon != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Icon(icon, size: 18, color: color),
            ),
          Text(
            label,
            style: TextStyle(fontWeight: FontWeight.w700, color: color, fontSize: 14),
          ),
        ],
      ),
    );
  }

  static StatusChip offDuty() => const StatusChip(
        label: 'OFF DUTY',
        color: AppColors.offDuty,
        icon: Icons.radio_button_unchecked,
      );

  static StatusChip onDuty() => const StatusChip(
        label: 'ON DUTY · GPS active',
        color: AppColors.successText,
        pulse: true,
      );

  static StatusChip idle() => const StatusChip(
        label: 'IDLE',
        color: AppColors.warning,
        icon: Icons.pause_circle_outline,
      );
}
