import 'package:flutter/material.dart';

import '../../core/constants/app_assets.dart';
import '../../core/theme/app_spacing.dart';
import 'primary_button.dart';
import 'stitch_illustration.dart';

/// Offline / no-network state with stitch illustration.
class NoInternetView extends StatelessWidget {
  const NoInternetView({
    super.key,
    this.onRetry,
    this.message = 'Check your network or try again later.',
  });

  final VoidCallback? onRetry;
  final String message;

  static bool isOfflineMessage(String? value) {
    if (value == null) return false;
    final lower = value.toLowerCase();
    return lower.contains('no internet') ||
        lower.contains('offline') ||
        lower.contains('network');
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.screenEdge),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const StitchIllustration(
              asset: AppAssets.noInternetIllustration,
              height: 200,
              semanticLabel: 'No internet connection illustration',
            ),
            const SizedBox(height: 24),
            Text(
              'No Internet Connection',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.65),
                  ),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              PrimaryButton(
                label: 'Try again',
                onPressed: onRetry,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
