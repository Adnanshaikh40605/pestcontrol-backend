import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Primary action button with loading spinner and disabled state.
class LoadingActionButton extends StatelessWidget {
  const LoadingActionButton({
    super.key,
    required this.label,
    this.loadingLabel,
    this.icon,
    this.onPressed,
    this.isLoading = false,
    this.expanded = true,
  });

  final String label;
  final String? loadingLabel;
  final IconData? icon;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    final disabled = isLoading || onPressed == null;
    final displayLabel = isLoading ? (loadingLabel ?? label) : label;

    final child = ElevatedButton(
      onPressed: disabled ? null : onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.45),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: expanded ? MainAxisSize.max : MainAxisSize.min,
        children: [
          if (isLoading) ...[
            const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 8),
          ] else if (icon != null) ...[
            Icon(icon, size: 20),
            const SizedBox(width: 4),
          ],
          Flexible(
            child: Text(
              displayLabel,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: AppColors.onPrimary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        ],
      ),
    );

    return expanded ? SizedBox(width: double.infinity, child: child) : child;
  }
}
