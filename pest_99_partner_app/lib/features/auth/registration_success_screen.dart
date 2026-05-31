import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_assets.dart';
import '../../core/theme/app_spacing.dart';
import '../../shared/widgets/primary_button.dart';
import '../../shared/widgets/stitch_illustration.dart';

class RegistrationSuccessScreen extends StatelessWidget {
  const RegistrationSuccessScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.screenEdge),
          child: Column(
            children: [
              const Spacer(),
              const StitchIllustration(
                asset: AppAssets.registrationSuccessIllustration,
                height: 240,
                semanticLabel: 'Registration successful illustration',
              ),
              const SizedBox(height: 32),
              Text(
                'Registration Successful!',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),
              Text(
                'Your partner account has been created. An admin will approve your access on CRM — then you can log in and start accepting bookings.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.65),
                    ),
              ),
              const Spacer(),
              PrimaryButton(
                label: 'Continue to Login',
                onPressed: () => context.go('/login'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
