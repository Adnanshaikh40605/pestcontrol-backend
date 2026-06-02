import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../config/legal_config.dart';
import '../../core/theme/app_colors.dart';

/// Company + legal links for Play Console compliance (profile / settings).
class LegalSupportCard extends StatelessWidget {
  const LegalSupportCard({super.key});

  Future<void> _open(BuildContext context, String url) async {
    final uri = Uri.parse(url);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not open $url')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final links = <(String, String)>[
      ('Privacy Policy', LegalConfig.privacyPolicy),
      ('Terms & Conditions', LegalConfig.termsAndConditions),
      ('Refund Policy', LegalConfig.refundPolicy),
      ('Data Deletion', LegalConfig.dataDeletion),
      ('Delete Account (Web)', LegalConfig.deleteAccount),
      ('Contact Us', LegalConfig.contact),
    ];

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Legal & Support',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  LegalConfig.brandName,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                Text(
                  LegalConfig.companyLegalName,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  LegalConfig.supportEmail,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                Text(
                  LegalConfig.supportPhone,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          for (var i = 0; i < links.length; i++)
            ListTile(
              dense: true,
              title: Text(links[i].$1, style: Theme.of(context).textTheme.bodyMedium),
              trailing: const Icon(Icons.open_in_new, size: 18, color: AppColors.textSecondary),
              onTap: () => _open(context, links[i].$2),
            ),
        ],
      ),
    );
  }
}
