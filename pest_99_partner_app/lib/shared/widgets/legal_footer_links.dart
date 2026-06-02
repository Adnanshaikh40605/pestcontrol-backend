import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../config/legal_config.dart';

/// Privacy + Terms links on auth screens (Google Play policy).
class LegalFooterLinks extends StatelessWidget {
  const LegalFooterLinks({super.key});

  Future<void> _open(String url) async {
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final linkStyle = TextStyle(
      color: Theme.of(context).colorScheme.primary,
      fontWeight: FontWeight.w600,
    );
    final baseStyle = Theme.of(context).textTheme.bodySmall?.copyWith(
          color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
        );

    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Text.rich(
        textAlign: TextAlign.center,
        TextSpan(
          style: baseStyle,
          children: [
            const TextSpan(text: 'By continuing you agree to our '),
            TextSpan(
              text: 'Privacy Policy',
              style: linkStyle,
              recognizer: TapGestureRecognizer()..onTap = () => _open(LegalConfig.privacyPolicy),
            ),
            const TextSpan(text: ' and '),
            TextSpan(
              text: 'Terms',
              style: linkStyle,
              recognizer: TapGestureRecognizer()
                ..onTap = () => _open(LegalConfig.termsAndConditions),
            ),
            const TextSpan(text: '.'),
          ],
        ),
      ),
    );
  }
}
