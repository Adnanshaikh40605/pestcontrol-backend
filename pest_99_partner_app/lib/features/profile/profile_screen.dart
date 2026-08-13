import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/user_error.dart';
import '../../models/partner_earnings.dart';
import '../../providers/auth_provider.dart';
import '../../providers/bookings_provider.dart';
import '../../providers/profile_provider.dart';
import '../../services/earnings_service.dart';
import '../../shared/widgets/app_top_bar.dart';
import '../../shared/widgets/legal_support_card.dart';
import 'delete_account_dialog.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProfileProvider>().loadProfile(force: true);
    });
  }

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<ProfileProvider>();
    final counts = context.watch<BookingsProvider>().counts;
    final p = profile.profile;

    final available = p?.stats?.availableJobs ?? counts.available;
    final accepted = p?.stats?.acceptedJobs ?? counts.accepted;
    final completed = p?.stats?.completedJobs ?? counts.completed;

    return Scaffold(
      appBar: const AppTopBar(showAvatar: false, centerLogo: true),
      body: profile.loading && p == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () => profile.loadProfile(force: true),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.screenEdge,
                  AppSpacing.sectionGap,
                  AppSpacing.screenEdge,
                  100,
                ),
                children: [
                  if (profile.error != null && p == null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text(profile.error!, textAlign: TextAlign.center),
                    ),
                  _ProfileHeader(
                    fullName: profile.displayName,
                    mobile: p?.mobile ?? '',
                    role: p?.role ?? 'technician',
                    avatarUrl: profile.avatarUrl,
                    isActive: p?.isActive ?? true,
                  ),
                  if (p?.isSuspended == true) ...[
                    const SizedBox(height: AppSpacing.elementGap),
                    _SuspendedBanner(reason: p?.presence?.suspendReason ?? ''),
                  ],
                  const SizedBox(height: AppSpacing.sectionGap),
                  _PresenceToggle(
                    presence: p?.presence,
                    onChanged: (online) => _setPresence(context, online),
                  ),
                  const SizedBox(height: AppSpacing.sectionGap),
                  _StatsGrid(
                    available: available,
                    accepted: accepted,
                    completed: completed,
                  ),
                  const SizedBox(height: AppSpacing.sectionGap),
                  const LegalSupportCard(),
                  const SizedBox(height: AppSpacing.sectionGap),
                  _MenuList(
                    onEditProfile: () => context.push('/profile/edit'),
                    onEarnings: () => context.push('/earnings'),
                    onLeave: () => context.push('/leave-requests'),
                    onDeleteAccount: () => _deleteAccount(context),
                    onLogout: () async {
                      context.read<ProfileProvider>().clear();
                      await context.read<AuthProvider>().logout();
                      if (context.mounted) context.go('/login');
                    },
                  ),
                ],
              ),
            ),
    );
  }

  Future<void> _deleteAccount(BuildContext context) async {
    final password = await showDeleteAccountDialog(context);
    if (password == null || !context.mounted) return;

    final auth = context.read<AuthProvider>();
    final ok = await auth.deleteAccount(password);
    if (!context.mounted) return;

    if (ok) {
      context.read<ProfileProvider>().clear();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Your account has been permanently deleted.')),
      );
      context.go('/login');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(auth.error ?? 'Account deletion failed')),
      );
    }
  }

  Future<void> _setPresence(BuildContext context, bool online) async {
    try {
      await EarningsService(context.read<ApiClient>()).setPresence(
        online ? 'online' : 'offline',
      );
      if (!context.mounted) return;
      await context.read<ProfileProvider>().loadProfile(force: true);
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(userErrorMessage(e, fallback: 'Could not update presence.'))),
      );
    }
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({
    required this.fullName,
    required this.mobile,
    required this.role,
    this.avatarUrl,
    required this.isActive,
  });

  final String fullName;
  final String mobile;
  final String role;
  final String? avatarUrl;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final initials = fullName.isNotEmpty ? fullName.substring(0, 1).toUpperCase() : '?';
    final roleLabel = role == 'technician_admin' ? 'Technician Admin' : 'Technician';

    return Container(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(color: Color(0x0A000000), blurRadius: 8, offset: Offset(0, 2)),
        ],
      ),
      child: Column(
        children: [
          Stack(
            children: [
              CircleAvatar(
                radius: 48,
                backgroundColor: AppColors.primaryContainer,
                backgroundImage:
                    avatarUrl != null && avatarUrl!.isNotEmpty ? NetworkImage(avatarUrl!) : null,
                child: avatarUrl == null || avatarUrl!.isEmpty
                    ? Text(
                        initials,
                        style: const TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primary,
                        ),
                      )
                    : null,
              ),
              if (isActive)
                Positioned(
                  right: 0,
                  bottom: 0,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: AppColors.successBg,
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.surface, width: 2),
                    ),
                    child: const Icon(Icons.verified, size: 16, color: AppColors.successText),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Text(fullName, style: Theme.of(context).textTheme.headlineMedium),
          if (mobile.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              mobile,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
            ),
          ],
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.primaryContainer,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              roleLabel,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppColors.onPrimary),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  const _StatsGrid({
    required this.available,
    required this.accepted,
    required this.completed,
  });

  final int available;
  final int accepted;
  final int completed;

  @override
  Widget build(BuildContext context) {
    final stats = [
      (Icons.inbox_outlined, '$available', 'Available', AppColors.primary),
      (Icons.assignment_turned_in_outlined, '$accepted', 'Accepted', AppColors.infoBlue),
      (Icons.task_alt, '$completed', 'Completed', AppColors.successText),
      (Icons.work_outline, '${available + accepted + completed}', 'All Jobs', AppColors.warning),
    ];

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: AppSpacing.elementGap,
      crossAxisSpacing: AppSpacing.elementGap,
      childAspectRatio: 1.35,
      children: stats.map((s) {
        return Container(
          padding: const EdgeInsets.all(AppSpacing.cardPadding),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(s.$1, size: 32, color: s.$4),
              const SizedBox(height: 8),
              Text(s.$2, style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 4),
              Text(
                s.$3.toUpperCase(),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                      letterSpacing: 0.5,
                    ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _SuspendedBanner extends StatelessWidget {
  const _SuspendedBanner({required this.reason});

  final String reason;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      decoration: BoxDecoration(
        color: AppColors.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Account suspended',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: AppColors.onErrorContainer,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            reason.isNotEmpty ? reason : 'Contact CRM admin to reactivate.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.onErrorContainer,
                ),
          ),
        ],
      ),
    );
  }
}

class _PresenceToggle extends StatelessWidget {
  const _PresenceToggle({required this.presence, required this.onChanged});

  final PartnerPresence? presence;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final suspended = presence?.isSuspended == true;
    final status = presence?.presenceStatus ?? 'offline';
    final locked = suspended ||
        status == 'busy' ||
        status == 'on_service' ||
        status == 'on_leave';
    final online = presence?.isOnline == true;
    final label = suspended
        ? 'Suspended'
        : status.replaceAll('_', ' ');

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Availability'),
        subtitle: Text(
          locked && !suspended
              ? '$label — finish current job before changing'
              : label,
        ),
        value: online && !locked,
        onChanged: locked ? null : onChanged,
      ),
    );
  }
}

class _MenuList extends StatelessWidget {
  const _MenuList({
    required this.onEditProfile,
    required this.onEarnings,
    required this.onLeave,
    required this.onDeleteAccount,
    required this.onLogout,
  });

  final VoidCallback onEditProfile;
  final VoidCallback onEarnings;
  final VoidCallback onLeave;
  final VoidCallback onDeleteAccount;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    final items = <(IconData, String, VoidCallback)>[
      (Icons.person_outline, 'Edit Profile', onEditProfile),
      (Icons.card_giftcard_outlined, 'Refer Client', () => context.push('/refer-client')),
      (Icons.timeline_outlined, 'My Referrals', () => context.push('/referral-progress')),
      (Icons.payments_outlined, 'Earnings History', onEarnings),
      (Icons.event_busy_outlined, 'Leave Requests', onLeave),
      (Icons.account_balance_outlined, 'Bank Details', () {}),
      (Icons.help_outline, 'Help & Support', () {}),
    ];

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          for (var i = 0; i < items.length; i++) ...[
            ListTile(
              leading: Icon(items[i].$1, color: AppColors.onSurfaceVariant),
              title: Text(items[i].$2),
              trailing: const Icon(Icons.chevron_right, color: AppColors.textSecondary),
              onTap: items[i].$3,
            ),
            if (i < items.length - 1) const Divider(height: 1, indent: 16, endIndent: 16),
          ],
          ListTile(
            leading: const Icon(Icons.delete_forever_outlined, color: AppColors.danger),
            title: Text(
              'Delete Account',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.danger,
                    fontWeight: FontWeight.w600,
                  ),
            ),
            onTap: onDeleteAccount,
          ),
          const Divider(height: 1, indent: 16, endIndent: 16),
          ListTile(
            leading: const Icon(Icons.logout, color: AppColors.danger),
            title: Text(
              'Logout',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.danger,
                    fontWeight: FontWeight.w600,
                  ),
            ),
            onTap: onLogout,
          ),
        ],
      ),
    );
  }
}
