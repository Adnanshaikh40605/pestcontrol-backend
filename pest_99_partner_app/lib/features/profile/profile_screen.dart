import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/auth_provider.dart';
import '../../providers/bookings_provider.dart';
import '../../providers/profile_provider.dart';
import '../../shared/widgets/app_snackbar.dart';
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
                    serviceCities: p?.serviceCities ?? const [],
                  ),
                  if (p?.isSuspended == true) ...[
                    const SizedBox(height: AppSpacing.elementGap),
                    _SuspendedBanner(reason: p?.presence?.suspendReason ?? ''),
                  ],
                  const SizedBox(height: AppSpacing.sectionGap),
                  _EarningsProgressCard(
                    jobsDone: completed,
                    totalEarnings: p?.stats?.totalEarnings ?? '0',
                    onOpenEarnings: () => context.push('/earnings'),
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
      AppSnackBar.success(context, 'Your account has been permanently deleted.');
      context.go('/login');
    } else {
      AppSnackBar.error(context, auth.error ?? 'Account deletion failed');
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
    this.serviceCities = const [],
  });

  final String fullName;
  final String mobile;
  final String role;
  final String? avatarUrl;
  final bool isActive;
  final List<String> serviceCities;

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
          if (serviceCities.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              'Service Areas',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: serviceCities
                  .map(
                    (city) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: AppColors.successBg,
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Text(
                        city,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: AppColors.successText,
                            ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
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

class _EarningsProgressCard extends StatelessWidget {
  const _EarningsProgressCard({
    required this.jobsDone,
    required this.totalEarnings,
    required this.onOpenEarnings,
  });

  final int jobsDone;
  final String totalEarnings;
  final VoidCallback onOpenEarnings;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        onTap: onOpenEarnings,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.border),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                AppColors.primary.withValues(alpha: 0.10),
                AppColors.surface,
              ],
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.payments_outlined, color: AppColors.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Your earnings progress',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ),
                  Text(
                    'History',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const Icon(Icons.chevron_right, color: AppColors.primary, size: 20),
                ],
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '$jobsDone',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                        Text(
                          'Jobs completed',
                          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                                color: AppColors.textSecondary,
                              ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          totalEarnings.startsWith('₹')
                              ? totalEarnings
                              : '₹$totalEarnings',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.w800,
                                color: AppColors.primary,
                              ),
                        ),
                        Text(
                          'Your share (40%)',
                          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                                color: AppColors.textSecondary,
                              ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                'This is your technician money only. Company share is separate and not paid to you.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ],
          ),
        ),
      ),
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
