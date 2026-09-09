import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../models/partner_earnings.dart';
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
                    statusLabel: p?.statusLabel ?? 'Active',
                    presenceStatus: p?.presence?.presenceStatus,
                    serviceCities: p?.serviceCities ?? const [],
                    baseServices: p?.baseServices ?? const [],
                  ),
                  if (p?.isUnavailable == true) ...[
                    const SizedBox(height: AppSpacing.elementGap),
                    _StatusBanner(
                      onLeave: p?.isOnLeave == true,
                      reason: p?.presence?.unavailableReason ??
                          p?.presence?.suspendReason ??
                          '',
                    ),
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
    this.statusLabel = 'Active',
    this.presenceStatus,
    this.serviceCities = const [],
    this.baseServices = const [],
  });

  final String fullName;
  final String mobile;
  final String role;
  final String? avatarUrl;
  final bool isActive;

  /// "Active" / "On Leave" / "Suspended", as set by the CRM desk.
  final String statusLabel;
  final String? presenceStatus;
  final List<String> serviceCities;
  final List<String> baseServices;

  bool get _onLeave => presenceStatus == PartnerPresence.statusOnLeave;
  bool get _suspended => presenceStatus == PartnerPresence.statusSuspended;

  Color get _statusBackground {
    if (_suspended) return AppColors.errorContainer;
    if (_onLeave) return const Color(0xFFFFFBE6);
    return AppColors.successBg;
  }

  Color get _statusForeground {
    if (_suspended) return AppColors.onErrorContainer;
    if (_onLeave) return const Color(0xFF874D00);
    return AppColors.primaryDark;
  }

  @override
  Widget build(BuildContext context) {
    final initials = _profileInitials(fullName);
    final roleLabel = role == 'technician_admin' ? 'Technician Admin' : 'Technician';
    const avatarSize = 88.0;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.cardPadding,
        vertical: 20,
      ),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(color: Color(0x0A000000), blurRadius: 10, offset: Offset(0, 2)),
        ],
      ),
      child: Column(
        children: [
          SizedBox(
            width: avatarSize + 8,
            height: avatarSize + 8,
            child: Stack(
              clipBehavior: Clip.none,
              alignment: Alignment.center,
              children: [
                Container(
                  width: avatarSize,
                  height: avatarSize,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.surface,
                    border: Border.all(color: AppColors.border, width: 2),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x14000000),
                        blurRadius: 8,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                  child: ClipOval(
                    child: avatarUrl != null && avatarUrl!.isNotEmpty
                        ? Image.network(
                            avatarUrl!,
                            width: avatarSize,
                            height: avatarSize,
                            fit: BoxFit.cover,
                            errorBuilder: (_, _, _) => _InitialAvatar(initials: initials),
                          )
                        : _InitialAvatar(initials: initials),
                  ),
                ),
                if (isActive)
                  Positioned(
                    right: 0,
                    bottom: 0,
                    child: Container(
                      width: 26,
                      height: 26,
                      decoration: BoxDecoration(
                        color: AppColors.successText,
                        shape: BoxShape.circle,
                        border: Border.all(color: AppColors.surface, width: 2.5),
                      ),
                      child: const Icon(
                        Icons.verified,
                        size: 14,
                        color: Colors.white,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Text(
            fullName,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  height: 1.2,
                ),
          ),
          if (mobile.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              mobile,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w500,
                  ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.successBg,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: AppColors.border),
                ),
                child: Text(
                  roleLabel,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: AppColors.primaryDark,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              // Shown for every status, not just the bad ones, so a technician
              // can always confirm what the office has them set to.
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: _statusBackground,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: AppColors.border),
                ),
                child: Text(
                  statusLabel,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: _statusForeground,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
          if (baseServices.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Base Services',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: baseServices
                  .map(
                    (service) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: AppColors.successBg,
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Text(
                        service,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: AppColors.primaryDark,
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
          if (serviceCities.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Service Areas',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: serviceCities
                  .map(
                    (city) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Text(
                        city,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: AppColors.onSurfaceVariant,
                              fontWeight: FontWeight.w600,
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

String _profileInitials(String fullName) {
  final parts = fullName.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
  if (parts.isEmpty) return '?';
  if (parts.length == 1) {
    return parts.first.substring(0, 1).toUpperCase();
  }
  return '${parts.first.substring(0, 1)}${parts.last.substring(0, 1)}'.toUpperCase();
}

class _InitialAvatar extends StatelessWidget {
  const _InitialAvatar({required this.initials});

  final String initials;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.successBg,
      alignment: Alignment.center,
      child: Text(
        initials,
        style: const TextStyle(
          fontSize: 30,
          fontWeight: FontWeight.w700,
          color: AppColors.primaryDark,
          height: 1,
          letterSpacing: 0.5,
        ),
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

/// Shown when the office has marked this technician on leave or suspended.
class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.onLeave, required this.reason});

  final bool onLeave;
  final String reason;

  @override
  Widget build(BuildContext context) {
    // Leave is a temporary absence rather than a problem, so it gets a warning
    // tone instead of the error tone used for suspension.
    final background =
        onLeave ? const Color(0xFFFFFBE6) : AppColors.errorContainer;
    final foreground =
        onLeave ? const Color(0xFF874D00) : AppColors.onErrorContainer;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            onLeave ? 'You are on leave' : 'Account suspended',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: foreground,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            reason.isNotEmpty
                ? reason
                : onLeave
                    ? 'New bookings are not being sent to you while you are on leave.'
                    : 'Contact CRM admin to reactivate.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: foreground,
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
