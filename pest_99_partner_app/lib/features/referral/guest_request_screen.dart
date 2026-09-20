import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/user_error.dart';
import '../../services/auth_service.dart';
import '../../services/referral_service.dart';
import '../../shared/widgets/app_snackbar.dart';
import '../../shared/widgets/app_text_field.dart';
import '../../shared/widgets/primary_button.dart';

/// Technician-sourced guest / client inquiry for CRM conversion.
class GuestRequestScreen extends StatefulWidget {
  const GuestRequestScreen({super.key});

  @override
  State<GuestRequestScreen> createState() => _GuestRequestScreenState();
}

class _GuestRequestScreenState extends State<GuestRequestScreen> {
  static const _serviceOptions = <String>[
    'Cockroach / Ants Control',
    'Bed Bug Control',
    'Termite Control',
    'Rodent Control',
    'Mosquito Control',
    'General Pest Control',
    'Other',
  ];

  final _name = TextEditingController();
  final _mobile = TextEditingController();
  final _area = TextEditingController();
  final _notes = TextEditingController();
  String? _serviceType;
  DateTime? _preferredDate;
  bool _saving = false;

  @override
  void dispose() {
    _name.dispose();
    _mobile.dispose();
    _area.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _preferredDate ?? now,
      firstDate: now,
      lastDate: now.add(const Duration(days: 90)),
    );
    if (picked != null) setState(() => _preferredDate = picked);
  }

  Future<void> _submit() async {
    final name = _name.text.trim();
    final mobile = AuthService.normalizeMobile(_mobile.text);
    if (name.isEmpty || mobile.isEmpty) {
      AppSnackBar.error(context, 'Please enter client name and mobile number.');
      return;
    }
    if (mobile.length != 10) {
      AppSnackBar.error(context, 'Please enter a valid 10-digit mobile number.');
      return;
    }
    setState(() => _saving = true);
    try {
      final preferred = _preferredDate == null
          ? null
          : '${_preferredDate!.year.toString().padLeft(4, '0')}-'
              '${_preferredDate!.month.toString().padLeft(2, '0')}-'
              '${_preferredDate!.day.toString().padLeft(2, '0')}';
      final referral = await ReferralService(context.read<ApiClient>()).submitGuestRequest(
        clientName: name,
        mobile: mobile,
        area: _area.text.trim(),
        serviceType: _serviceType,
        preferredDate: preferred,
        notes: _notes.text.trim(),
      );
      if (!mounted) return;
      AppSnackBar.success(context, 'Guest request sent to CRM.');
      context.push('/referral-progress', extra: referral.id);
    } catch (e) {
      if (mounted) {
        AppSnackBar.error(
          context,
          userErrorMessage(e, fallback: 'Could not submit guest request.'),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateLabel = _preferredDate == null
        ? 'Select preferred date (optional)'
        : '${_preferredDate!.day}/${_preferredDate!.month}/${_preferredDate!.year}';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Guest Request'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.screenEdge),
        children: [
          Text(
            'Request a guest booking',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Create a client inquiry from the field. CRM will contact the guest and convert to a booking.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                ),
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          AppTextField(label: 'Client Name', hint: 'Full name', controller: _name),
          const SizedBox(height: AppSpacing.elementGap),
          AppTextField(
            label: 'Mobile Number',
            hint: '10-digit mobile',
            controller: _mobile,
            keyboardType: TextInputType.phone,
          ),
          const SizedBox(height: AppSpacing.elementGap),
          AppTextField(label: 'Area / Locality', hint: 'Optional', controller: _area),
          const SizedBox(height: AppSpacing.elementGap),
          Text('Service type', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            // ignore: deprecated_member_use — controlled selection; initialValue is one-shot
            value: _serviceType,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              hintText: 'Select service (optional)',
            ),
            items: _serviceOptions
                .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                .toList(),
            onChanged: (v) => setState(() => _serviceType = v),
          ),
          const SizedBox(height: AppSpacing.elementGap),
          OutlinedButton.icon(
            onPressed: _pickDate,
            icon: const Icon(Icons.calendar_today_outlined),
            label: Text(dateLabel),
          ),
          const SizedBox(height: AppSpacing.elementGap),
          AppTextField(
            label: 'Notes',
            hint: 'Pest issue, access notes, etc.',
            controller: _notes,
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          PrimaryButton(
            label: _saving ? 'Submitting…' : 'Submit guest request',
            onPressed: _saving ? null : _submit,
          ),
        ],
      ),
    );
  }
}
