import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/constants/app_assets.dart';
import '../../core/theme/app_spacing.dart';
import '../../services/referral_service.dart';
import '../../shared/widgets/app_text_field.dart';
import '../../shared/widgets/primary_button.dart';
import '../../shared/widgets/stitch_illustration.dart';

class ReferClientScreen extends StatefulWidget {
  const ReferClientScreen({super.key});

  @override
  State<ReferClientScreen> createState() => _ReferClientScreenState();
}

class _ReferClientScreenState extends State<ReferClientScreen> {
  final _name = TextEditingController();
  final _mobile = TextEditingController();
  final _area = TextEditingController();
  bool _saving = false;

  @override
  void dispose() {
    _name.dispose();
    _mobile.dispose();
    _area.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _saving = true);
    try {
      final referral = await ReferralService(context.read<ApiClient>()).submitReferral(
        clientName: _name.text.trim(),
        mobile: _mobile.text.trim(),
        area: _area.text.trim(),
      );
      if (!mounted) return;
      context.push('/referral-progress', extra: referral.id);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Refer Client'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.screenEdge),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: const StitchIllustration(
              asset: AppAssets.referralPromotional,
              height: 200,
              fit: BoxFit.cover,
              semanticLabel: 'Refer a client promotional banner',
            ),
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          Text('Refer a new client', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'Share client details — saved to CRM inquiries.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                ),
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          AppTextField(label: 'Client Name', hint: 'Enter client full name', controller: _name),
          const SizedBox(height: AppSpacing.elementGap),
          AppTextField(
            label: 'Mobile Number',
            hint: 'Enter client mobile number',
            keyboardType: TextInputType.phone,
            controller: _mobile,
          ),
          const SizedBox(height: AppSpacing.elementGap),
          AppTextField(label: 'Area / Location', hint: 'Enter service area', controller: _area),
          const SizedBox(height: AppSpacing.sectionGap),
          PrimaryButton(
            label: _saving ? 'Submitting…' : 'Submit Referral',
            onPressed: _saving ? null : _submit,
          ),
        ],
      ),
    );
  }
}
