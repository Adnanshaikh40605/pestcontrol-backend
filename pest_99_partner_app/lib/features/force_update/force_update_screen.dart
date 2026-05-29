import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/app_update_provider.dart';
import '../../shared/widgets/pest_logo.dart';
import '../../shared/widgets/primary_button.dart';

/// Full-screen block when the installed APK is below minimum supported version.
class ForceUpdateScreen extends StatelessWidget {
  const ForceUpdateScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final update = context.watch<AppUpdateProvider>();
    final info = update.serverInfo;
    final title = info?.updateTitle ?? 'New Update Available';
    final latest = info?.latestVersion ?? '—';

    return PopScope(
      canPop: false,
      child: Scaffold(
        backgroundColor: AppColors.surface,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.screenEdge),
            child: Column(
              children: [
                const SizedBox(height: 32),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x14000000),
                        blurRadius: 16,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                  child: const PestLogo(height: 72),
                ),
                const SizedBox(height: 28),
                Icon(
                  Icons.system_update_alt_rounded,
                  size: 56,
                  color: AppColors.primary.withValues(alpha: 0.9),
                ),
                const SizedBox(height: 20),
                Text(
                  title,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                ),
                const SizedBox(height: 20),
                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (info != null && info.updateMessage.isNotEmpty) ...[
                          Text(
                            info.updateMessage,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: AppColors.textSecondary,
                                  height: 1.45,
                                ),
                          ),
                          const SizedBox(height: 24),
                        ],
                        _VersionCard(
                          label: 'Your current version',
                          value: 'v${update.currentVersion}',
                        ),
                        const SizedBox(height: 12),
                        _VersionCard(
                          label: 'Latest version',
                          value: 'v$latest',
                          highlight: true,
                        ),
                        const SizedBox(height: 24),
                        Text(
                          'Please uninstall the current app and install the latest version shared by the company.',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary,
                                height: 1.4,
                              ),
                        ),
                      ],
                    ),
                  ),
                ),
                PrimaryButton(
                  label: 'OK',
                  onPressed: () => SystemNavigator.pop(),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _VersionCard extends StatelessWidget {
  const _VersionCard({
    required this.label,
    required this.value,
    this.highlight = false,
  });

  final String label;
  final String value;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: highlight ? AppColors.primary.withValues(alpha: 0.08) : AppColors.background,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: highlight ? AppColors.primary.withValues(alpha: 0.35) : AppColors.border,
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: highlight ? AppColors.primary : AppColors.textPrimary,
                ),
          ),
        ],
      ),
    );
  }
}
