import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/app_update_provider.dart';

/// Soft "Update Available" dialog when install is behind latest but not forced.
class UpdateAvailableHost extends StatefulWidget {
  const UpdateAvailableHost({
    super.key,
    required this.child,
    required this.playStorePackageId,
  });

  final Widget child;
  final String playStorePackageId;

  @override
  State<UpdateAvailableHost> createState() => _UpdateAvailableHostState();
}

class _UpdateAvailableHostState extends State<UpdateAvailableHost> {
  static const _prefsKey = 'soft_update_dismissed_for';
  bool _promptOpen = false;
  String? _lastPromptedLatest;

  Future<void> _maybePrompt() async {
    if (!mounted || _promptOpen) return;
    final provider = context.read<AppUpdateProvider>();
    if (provider.forceUpdateRequired) return;
    if (!provider.updateAvailable) return;

    final latest = provider.serverInfo?.latestVersion.trim() ?? '';
    if (latest.isEmpty) return;
    if (_lastPromptedLatest == latest) return;

    final prefs = await SharedPreferences.getInstance();
    final dismissedFor = prefs.getString(_prefsKey);
    if (dismissedFor == latest) return;
    if (!mounted) return;

    _lastPromptedLatest = latest;
    _promptOpen = true;
    final info = provider.serverInfo;
    final title = (info?.updateTitle.trim().isNotEmpty ?? false)
        ? info!.updateTitle.trim()
        : 'Update Available';
    final message = (info?.updateMessage.trim().isNotEmpty ?? false)
        ? info!.updateMessage.trim()
        : 'A newer version is available on the Play Store. Please update for the latest features and fixes.';
    final url = info?.storeUrl ??
        'https://play.google.com/store/apps/details?id=${widget.playStorePackageId}';

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text(title, textAlign: TextAlign.center),
          content: Text(message, textAlign: TextAlign.center),
          actionsAlignment: MainAxisAlignment.center,
          actions: [
            TextButton(
              onPressed: () async {
                await prefs.setString(_prefsKey, latest);
                if (ctx.mounted) Navigator.of(ctx).pop();
              },
              child: const Text('Later'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
              onPressed: () => _openStore(url),
              child: const Text('Update'),
            ),
          ],
        );
      },
    );

    _promptOpen = false;
  }

  Future<void> _openStore(String url) async {
    final https = Uri.parse(url);
    final market = Uri.parse('market://details?id=${widget.playStorePackageId}');
    if (await canLaunchUrl(market)) {
      final ok = await launchUrl(market, mode: LaunchMode.externalApplication);
      if (ok) return;
    }
    await launchUrl(https, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppUpdateProvider>(
      builder: (context, provider, _) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _maybePrompt());
        return widget.child;
      },
    );
  }
}
