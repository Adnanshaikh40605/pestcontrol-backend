import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/models/app_version_info.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/primary_button.dart';

/// Blocking mandatory-update gate. No dismiss / skip / later.
class ForceUpdateScreen extends StatelessWidget {
  const ForceUpdateScreen({super.key, this.storeUrl});

  final String? storeUrl;

  Future<void> _openPlayStore() async {
    final https = Uri.parse(storeUrl ?? AppVersionInfo.defaultStoreUrl);
    final market = Uri.parse('market://details?id=com.pestcontrol99.partner');

    if (await canLaunchUrl(market)) {
      final ok = await launchUrl(market, mode: LaunchMode.externalApplication);
      if (ok) return;
    }
    await launchUrl(https, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Scaffold(
        backgroundColor: AppColors.surface,
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 360),
                child: Material(
                  color: Colors.white,
                  elevation: 8,
                  shadowColor: const Color(0x33000000),
                  borderRadius: BorderRadius.circular(16),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.system_update_alt_rounded,
                          size: 48,
                          color: AppColors.primary.withValues(alpha: 0.95),
                        ),
                        const SizedBox(height: 20),
                        Text(
                          'Please update the app.',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.w700,
                                color: AppColors.textPrimary,
                              ),
                        ),
                        const SizedBox(height: 24),
                        PrimaryButton(
                          label: 'Update',
                          onPressed: _openPlayStore,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
