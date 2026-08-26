import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/models/app_version_info.dart';
import '../../core/theme/app_colors.dart';
import '../../providers/app_update_provider.dart';
import '../../shared/widgets/pc99_widgets.dart';

/// Blocking mandatory-update gate. No dismiss / skip / later.
class ForceUpdateScreen extends StatelessWidget {
  const ForceUpdateScreen({super.key, this.storeUrl});

  final String? storeUrl;

  Future<void> _openPlayStore(String url) async {
    final https = Uri.parse(url);
    final market = Uri.parse(
      'market://details?id=com.pestcontrol99.pest_99_customer_app',
    );

    if (await canLaunchUrl(market)) {
      final ok = await launchUrl(market, mode: LaunchMode.externalApplication);
      if (ok) return;
    }
    await launchUrl(https, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final info = context.watch<AppUpdateProvider>().serverInfo;
    final title = (info?.updateTitle.trim().isNotEmpty ?? false)
        ? info!.updateTitle.trim()
        : 'Update required';
    final message = (info?.updateMessage.trim().isNotEmpty ?? false)
        ? info!.updateMessage.trim()
        : 'A newer version of Pest Control 99 is required. Tap Update to continue.';
    final url = storeUrl ?? info?.storeUrl ?? AppVersionInfo.defaultStoreUrl;

    return PopScope(
      canPop: false,
      child: Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 360),
                child: Material(
                  color: Colors.white,
                  elevation: 6,
                  borderRadius: BorderRadius.circular(16),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.system_update_alt_rounded,
                          size: 48,
                          color: AppColors.primary,
                        ),
                        const SizedBox(height: 20),
                        Text(
                          title,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          message,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 14,
                            color: AppColors.textMuted,
                          ),
                        ),
                        const SizedBox(height: 24),
                        Pc99PrimaryButton(
                          label: 'Update',
                          onPressed: () => _openPlayStore(url),
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
