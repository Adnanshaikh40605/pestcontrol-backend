import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../config/legal_config.dart';
import '../../core/theme/app_colors.dart';

Future<void> openLegalUrl(String url) async {
  final uri = Uri.parse(url);
  await launchUrl(uri, mode: LaunchMode.externalApplication);
}

class LegalFooterLinks extends StatelessWidget {
  const LegalFooterLinks({super.key});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        _Link('Privacy', LegalConfig.privacyPolicy),
        const Text(' · ', style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
        _Link('Terms', LegalConfig.termsAndConditions),
        const Text(' · ', style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
        _Link('Contact', LegalConfig.contact),
      ],
    );
  }
}

class _Link extends StatelessWidget {
  const _Link(this.label, this.url);
  final String label;
  final String url;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => openLegalUrl(url),
      child: Text(
        label,
        style: const TextStyle(
          color: AppColors.primary,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          decoration: TextDecoration.underline,
        ),
      ),
    );
  }
}
