import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Yes/No confirmation before accept or reject on a new booking.
Future<bool> confirmBookingAccept(BuildContext context) {
  return _showYesNo(
    context,
    title: 'Accept booking?',
    message: 'Are you sure you want to accept this booking?',
    yesLabel: 'Yes, accept',
  );
}

Future<bool> confirmBookingReject(BuildContext context) {
  return _showYesNo(
    context,
    title: 'Reject booking?',
    message: 'Are you sure you want to reject this booking?',
    yesLabel: 'Yes, reject',
    yesIsDestructive: true,
  );
}

Future<bool> _showYesNo(
  BuildContext context, {
  required String title,
  required String message,
  required String yesLabel,
  bool yesIsDestructive = false,
}) async {
  final result = await showDialog<bool>(
    context: context,
    barrierDismissible: true,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('No'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: yesIsDestructive ? AppColors.danger : AppColors.primary,
            foregroundColor: Colors.white,
          ),
          onPressed: () => Navigator.of(ctx).pop(true),
          child: Text(yesLabel),
        ),
      ],
    ),
  );
  return result == true;
}
