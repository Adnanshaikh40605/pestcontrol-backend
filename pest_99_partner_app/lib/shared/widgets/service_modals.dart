import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/models/booking_type.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import 'primary_button.dart';

/// Returns local image path after capture, or null if cancelled.
Future<String?> showSelfieVerificationModal(BuildContext context) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => const _SelfieVerificationSheet(),
  );
}

Future<PaymentMode?> showEndServiceModal(BuildContext context) {
  return showModalBottomSheet<PaymentMode>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => const _EndServiceSheet(),
  );
}

class _SheetHandle extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 6,
      margin: const EdgeInsets.only(bottom: 24),
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(999),
      ),
    );
  }
}

class _SelfieVerificationSheet extends StatefulWidget {
  const _SelfieVerificationSheet();

  @override
  State<_SelfieVerificationSheet> createState() => _SelfieVerificationSheetState();
}

class _SelfieVerificationSheetState extends State<_SelfieVerificationSheet> {
  String? _previewPath;
  bool _busy = false;

  Future<void> _capture() async {
    setState(() => _busy = true);
    try {
      final file = await ImagePicker().pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
        preferredCameraDevice: CameraDevice.front,
      );
      if (file != null) setState(() => _previewPath = file.path);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
      ),
      padding: EdgeInsets.fromLTRB(
        AppSpacing.screenEdge,
        12,
        AppSpacing.screenEdge,
        MediaQuery.paddingOf(context).bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _SheetHandle(),
          Text('Verify Identity', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text(
            'Take a quick selfie to start the service visit.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 24),
          GestureDetector(
            onTap: _busy ? null : _capture,
            child: Container(
              height: 200,
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppColors.surfaceContainerLow,
                borderRadius: BorderRadius.circular(AppSpacing.baseRadius),
                border: Border.all(color: AppColors.border, width: 2),
                image: _previewPath != null
                    ? DecorationImage(
                        image: FileImage(File(_previewPath!)),
                        fit: BoxFit.cover,
                      )
                    : null,
              ),
              child: _previewPath == null
                  ? const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.photo_camera_outlined, size: 48, color: AppColors.primary),
                        SizedBox(height: 8),
                        Text('Tap to capture selfie'),
                      ],
                    )
                  : null,
            ),
          ),
          const SizedBox(height: 24),
          PrimaryButton(
            label: _busy
                ? 'Opening camera…'
                : _previewPath != null
                    ? 'Use photo & continue'
                    : 'Capture selfie',
            icon: Icons.camera_alt,
            onPressed: _busy
                ? null
                : _previewPath != null
                    ? () => Navigator.pop(context, _previewPath)
                    : _capture,
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }
}

class _EndServiceSheet extends StatefulWidget {
  const _EndServiceSheet();

  @override
  State<_EndServiceSheet> createState() => _EndServiceSheetState();
}

class _EndServiceSheetState extends State<_EndServiceSheet> {
  PaymentMode _mode = PaymentMode.cash;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
        boxShadow: [
          BoxShadow(color: Color(0x26000000), blurRadius: 40, offset: Offset(0, -8)),
        ],
      ),
      padding: EdgeInsets.fromLTRB(
        24,
        12,
        24,
        MediaQuery.paddingOf(context).bottom + 32,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(child: _SheetHandle()),
          Text('Complete Service', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text(
            'Please record the final payment mode to close the job.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(height: 24),
          Text('Payment Mode', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          DropdownButtonFormField<PaymentMode>(
            value: _mode,
            items: const [
              DropdownMenuItem(value: PaymentMode.cash, child: Text('Cash')),
              DropdownMenuItem(value: PaymentMode.online, child: Text('Online')),
            ],
            onChanged: (v) => setState(() => _mode = v ?? PaymentMode.cash),
          ),
          const SizedBox(height: 24),
          PrimaryButton(
            label: 'Confirm & Complete',
            icon: Icons.check_circle,
            onPressed: () => Navigator.pop(context, _mode),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }
}
