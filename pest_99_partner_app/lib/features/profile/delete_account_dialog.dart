import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../shared/widgets/app_text_field.dart';

/// Returns entered password when user confirms deletion, or null if cancelled.
Future<String?> showDeleteAccountDialog(BuildContext context) async {
  final passwordController = TextEditingController();
  var confirmed = false;

  final result = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (dialogContext) {
      return StatefulBuilder(
        builder: (context, setState) {
          return AlertDialog(
            title: const Text('Delete account permanently?'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'This will permanently delete your Pest 99 Partner account. '
                    'You will lose access to bookings, earnings history in the app, '
                    'and push notifications.\n\n'
                    'Completed service records may be retained for legal and billing purposes '
                    'as described in our Privacy Policy.\n\n'
                    'This action cannot be undone.',
                  ),
                  const SizedBox(height: 16),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: confirmed,
                    onChanged: (v) => setState(() => confirmed = v ?? false),
                    title: const Text(
                      'I understand this is permanent',
                      style: TextStyle(fontSize: 14),
                    ),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                  const SizedBox(height: 8),
                  AppTextField(
                    label: 'Confirm password',
                    hint: 'Enter your login password',
                    controller: passwordController,
                    obscureText: true,
                    onChanged: (_) => setState(() {}),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.danger,
                  disabledBackgroundColor: AppColors.danger.withValues(alpha: 0.4),
                ),
                onPressed: confirmed && passwordController.text.isNotEmpty
                    ? () => Navigator.of(dialogContext).pop(true)
                    : null,
                child: const Text('Delete my account'),
              ),
            ],
          );
        },
      );
    },
  );

  if (result != true) {
    passwordController.dispose();
    return null;
  }

  final password = passwordController.text;
  passwordController.dispose();
  return password;
}
