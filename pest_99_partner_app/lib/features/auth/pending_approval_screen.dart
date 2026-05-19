import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/auth_provider.dart';
import '../../services/profile_service.dart';
import '../../shared/widgets/pest_logo.dart';
import '../../shared/widgets/primary_button.dart';

class PendingApprovalScreen extends StatefulWidget {
  const PendingApprovalScreen({super.key});

  @override
  State<PendingApprovalScreen> createState() => _PendingApprovalScreenState();
}

class _PendingApprovalScreenState extends State<PendingApprovalScreen> {
  bool _checking = false;

  Future<void> _checkStatus() async {
    setState(() => _checking = true);
    try {
      final api = context.read<ApiClient>();
      final data = await ProfileService(api).getProfile();
      final approved = data['is_app_approved'] == true;
      await context.read<AuthProvider>().refreshApprovalFromProfile(data);
      if (!mounted) return;
      if (approved) {
        context.go('/bookings');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Still waiting for admin approval on CRM Technicians page.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.screenEdge),
          child: Column(
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () async {
                    await auth.logout();
                    if (context.mounted) context.go('/login');
                  },
                  child: const Text('Logout'),
                ),
              ),
              const Spacer(),
              const PestLogo(height: 80),
              const SizedBox(height: 24),
              Icon(Icons.hourglass_top, size: 64, color: AppColors.primary.withValues(alpha: 0.8)),
              const SizedBox(height: 16),
              Text('Awaiting approval', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 12),
              Text(
                'Your registration is complete. A Pest Control 99 admin must enable Partner App access '
                'on the CRM Technicians page before you can view and accept bookings.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
              ),
              if (auth.partnerName != null) ...[
                const SizedBox(height: 16),
                Text(auth.partnerName!, style: Theme.of(context).textTheme.titleMedium),
              ],
              const Spacer(),
              PrimaryButton(
                label: _checking ? 'Checking…' : 'Check approval status',
                onPressed: _checking ? null : _checkStatus,
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }
}
