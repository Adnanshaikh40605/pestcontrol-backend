import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/legal_config.dart';
import '../core/auth_gate.dart';
import '../core/theme/app_colors.dart';
import '../shared/widgets/legal_footer_links.dart';
import '../shared/widgets/pc99_widgets.dart';

/// Support tab — complaint, call, and help links.
class SupportHubScreen extends StatelessWidget {
  const SupportHubScreen({super.key});

  Future<void> _call() async {
    await launchUrl(Uri.parse(LegalConfig.supportPhoneTel));
  }

  Future<void> _email() async {
    await launchUrl(Uri.parse(LegalConfig.supportEmailMail));
  }

  @override
  Widget build(BuildContext context) {
    return Pc99Scaffold(
      brandTitle: true,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          const Text(
            'Support',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          const Text(
            'We’re here to help with bookings, service issues, and account questions.',
            style: TextStyle(color: AppColors.textMuted, fontSize: 13, height: 1.35),
          ),
          const SizedBox(height: 16),
          Pc99Card(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                _SupportTile(
                  icon: Icons.support_agent_rounded,
                  title: 'Complaint / Re-Service',
                  subtitle: 'Report an issue with a recent visit',
                  onTap: () => pushAuthed(context, '/complaint'),
                ),
                const Divider(height: 1, color: AppColors.divider),
                _SupportTile(
                  icon: Icons.phone_in_talk_outlined,
                  title: 'Call us',
                  subtitle: LegalConfig.supportPhone,
                  onTap: _call,
                ),
                const Divider(height: 1, color: AppColors.divider),
                _SupportTile(
                  icon: Icons.mail_outline_rounded,
                  title: 'Email support',
                  subtitle: LegalConfig.supportEmail,
                  onTap: _email,
                ),
                const Divider(height: 1, color: AppColors.divider),
                _SupportTile(
                  icon: Icons.help_outline_rounded,
                  title: 'Help centre',
                  subtitle: 'Contact & FAQs on our website',
                  onTap: () => openLegalUrl(LegalConfig.contact),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Pc99Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Quick links', style: TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () => context.push('/bookings'),
                  child: const Text('My bookings'),
                ),
                TextButton(
                  onPressed: () => pushAuthed(context, '/book/property'),
                  child: const Text('Book a service'),
                ),
                TextButton(
                  onPressed: () => context.push('/amc'),
                  child: const Text('My AMC'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SupportTile extends StatelessWidget {
  const _SupportTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      leading: Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: AppColors.successBg,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: AppColors.primary, size: 22),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
      subtitle: Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
      trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
    );
  }
}
