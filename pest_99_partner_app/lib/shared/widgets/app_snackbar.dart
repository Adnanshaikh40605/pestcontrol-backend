import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Consistent floating snackbars for success / error / info across the app.
abstract final class AppSnackBar {
  static void show(
    BuildContext context,
    String message, {
    bool error = false,
    bool success = false,
    IconData? icon,
    Duration duration = const Duration(seconds: 4),
  }) {
    if (message.trim().isEmpty) return;
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();

    Color? bg;
    if (error) {
      bg = Theme.of(context).colorScheme.error;
    } else if (success) {
      bg = AppColors.primary;
    }

    final resolvedIcon = icon ??
        (error
            ? Icons.error_outline
            : success
                ? Icons.check_circle_outline
                : null);

    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            if (resolvedIcon != null) ...[
              Icon(resolvedIcon, color: Colors.white, size: 20),
              const SizedBox(width: 8),
            ],
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: bg,
        behavior: SnackBarBehavior.floating,
        duration: duration,
      ),
    );
  }

  static void error(BuildContext context, String message) =>
      show(context, message, error: true);

  static void success(BuildContext context, String message) =>
      show(context, message, success: true);

  static void info(BuildContext context, String message) =>
      show(context, message);
}
