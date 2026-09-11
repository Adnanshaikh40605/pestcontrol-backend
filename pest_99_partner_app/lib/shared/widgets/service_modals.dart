import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/models/booking_type.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/utils/gst_breakdown.dart';
import '../../core/utils/money_format.dart';
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

/// Cash / Online collection sheet with customer GST breakdown.
///
/// Shown when ending a service (card or detail). Returns the chosen [PaymentMode]
/// or null if cancelled. Persists via complete booking API.
Future<PaymentMode?> showEndServiceModal(
  BuildContext context, {
  String? payableAmount,
  String? jobAmount,
  String? baseAmount,
  String? gstAmount,
  String? totalAmount,
  String? gstPercent,
  PaymentMode? initialMode,
}) {
  return showModalBottomSheet<PaymentMode>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => _EndServiceSheet(
      payableAmount: payableAmount,
      jobAmount: jobAmount,
      baseAmount: baseAmount,
      gstAmount: gstAmount,
      totalAmount: totalAmount,
      gstPercent: gstPercent,
      initialMode: initialMode,
    ),
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
            'Take a quick selfie to start the service visit. '
            'Camera access is used only for profile and job verification photos.',
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
  const _EndServiceSheet({
    this.payableAmount,
    this.jobAmount,
    this.baseAmount,
    this.gstAmount,
    this.totalAmount,
    this.gstPercent,
    this.initialMode,
  });

  final String? payableAmount;
  final String? jobAmount;
  final String? baseAmount;
  final String? gstAmount;
  final String? totalAmount;
  final String? gstPercent;
  final PaymentMode? initialMode;

  @override
  State<_EndServiceSheet> createState() => _EndServiceSheetState();
}

class _EndServiceSheetState extends State<_EndServiceSheet> {
  late PaymentMode _mode;
  bool _modeChosen = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode ?? PaymentMode.cash;
    _modeChosen = widget.initialMode != null;
  }

  @override
  Widget build(BuildContext context) {
    final payable = (widget.payableAmount ?? '').trim();
    final gst = GstBreakdown.resolve(
      baseAmount: widget.baseAmount,
      gstAmount: widget.gstAmount,
      totalAmount: widget.totalAmount,
      gstPercent: widget.gstPercent,
      inclusiveTotal: widget.jobAmount,
    );

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
          Text('Cash or Online?', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text(
            'Ask the customer how they want to pay. Some want the total with GST; '
            'others only care about the base price.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
          ),
          if (gst.hasAmount) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFECFDF5),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFA7F3D0)),
              ),
              child: Column(
                children: [
                  _GstRow(
                    label: 'Base price (excl. GST)',
                    value: MoneyFormat.rupees(gst.baseAmount),
                  ),
                  const SizedBox(height: 8),
                  _GstRow(
                    label: gst.gstLabel,
                    value: MoneyFormat.rupees(gst.gstAmount),
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 10),
                    child: Divider(height: 1, color: Color(0xFFA7F3D0)),
                  ),
                  _GstRow(
                    label: 'Total (incl. GST)',
                    value: MoneyFormat.rupees(gst.totalAmount),
                    emphasize: true,
                  ),
                  if (payable.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    _GstRow(
                      label: 'Your share (excl. GST)',
                      value: MoneyFormat.rupees(payable),
                    ),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 24),
          Text(
            'Payment mode (required)',
            style: Theme.of(context).textTheme.labelLarge,
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _PaymentModeChip(
                  label: 'Cash',
                  icon: Icons.payments_outlined,
                  selected: _modeChosen && _mode == PaymentMode.cash,
                  onTap: () => setState(() {
                    _mode = PaymentMode.cash;
                    _modeChosen = true;
                  }),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _PaymentModeChip(
                  label: 'Online',
                  icon: Icons.qr_code_2_outlined,
                  selected: _modeChosen && _mode == PaymentMode.online,
                  onTap: () => setState(() {
                    _mode = PaymentMode.online;
                    _modeChosen = true;
                  }),
                ),
              ),
            ],
          ),
          if (!_modeChosen) ...[
            const SizedBox(height: 8),
            Text(
              'Tap Cash or Online to continue.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
            ),
          ],
          const SizedBox(height: 24),
          PrimaryButton(
            label: 'Confirm & Complete',
            icon: Icons.check_circle,
            onPressed: _modeChosen ? () => Navigator.pop(context, _mode) : null,
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

class _GstRow extends StatelessWidget {
  const _GstRow({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: emphasize
                      ? const Color(0xFF047857)
                      : AppColors.onSurface,
                  fontWeight: emphasize ? FontWeight.w700 : FontWeight.w500,
                ),
          ),
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: emphasize ? FontWeight.w800 : FontWeight.w600,
                color: const Color(0xFF047857),
              ),
        ),
      ],
    );
  }
}

class _PaymentModeChip extends StatelessWidget {
  const _PaymentModeChip({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? AppColors.primary.withValues(alpha: 0.12) : AppColors.surfaceContainerLow,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: selected ? AppColors.primary : AppColors.border,
              width: selected ? 2 : 1,
            ),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                size: 28,
                color: selected ? AppColors.primary : AppColors.onSurfaceVariant,
              ),
              const SizedBox(height: 6),
              Text(
                label,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: selected ? AppColors.primary : AppColors.onSurface,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
