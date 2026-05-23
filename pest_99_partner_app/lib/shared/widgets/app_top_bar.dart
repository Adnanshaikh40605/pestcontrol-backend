import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/notifications_provider.dart';
import 'pest_logo.dart';

class AppTopBar extends StatelessWidget implements PreferredSizeWidget {
  const AppTopBar({
    super.key,
    this.showAvatar = true,
    this.showBack = false,
    this.onBack,
    this.centerLogo = true,
    this.title,
    this.avatarUrl,
    this.avatarLabel,
    this.onAvatarTap,
  });

  final bool showAvatar;
  final bool showBack;
  final VoidCallback? onBack;
  final bool centerLogo;
  final String? title;
  final String? avatarUrl;
  final String? avatarLabel;
  final VoidCallback? onAvatarTap;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  void _defaultAvatarTap(BuildContext context) {
    context.go('/profile');
  }

  @override
  Widget build(BuildContext context) {
    final unread = context.watch<NotificationsProvider>().unreadCount;

    return Material(
      color: AppColors.surface,
      child: Container(
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: AppColors.border)),
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.screenEdge,
          vertical: 12,
        ),
        child: SafeArea(
          bottom: false,
          child: Row(
            children: [
              if (showBack)
                IconButton(
                  onPressed: onBack ?? () => Navigator.of(context).maybePop(),
                  icon: const Icon(Icons.arrow_back, color: AppColors.onSurfaceVariant),
                  style: IconButton.styleFrom(
                    minimumSize: const Size(48, 48),
                  ),
                )
              else if (showAvatar)
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: onAvatarTap ?? () => _defaultAvatarTap(context),
                    customBorder: const CircleBorder(),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: _AvatarChip(url: avatarUrl, label: avatarLabel),
                    ),
                  ),
                )
              else
                const SizedBox(width: 48),
              Expanded(
                child: centerLogo
                    ? const Center(child: PestLogo(height: 32))
                    : Text(
                        title ?? '',
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                              color: AppColors.primary,
                            ),
                        textAlign: TextAlign.center,
                      ),
              ),
              IconButton(
                onPressed: () => context.push('/notifications'),
                icon: Badge(
                  isLabelVisible: unread > 0,
                  label: Text(unread > 9 ? '9+' : '$unread'),
                  child: const Icon(Icons.notifications_outlined, color: AppColors.onSurfaceVariant),
                ),
                style: IconButton.styleFrom(minimumSize: const Size(40, 40)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AvatarChip extends StatelessWidget {
  const _AvatarChip({this.url, this.label});

  final String? url;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final initials = (label != null && label!.trim().isNotEmpty)
        ? label!.trim().substring(0, 1).toUpperCase()
        : '?';

    if (url != null && url!.isNotEmpty) {
      return CircleAvatar(
        radius: 20,
        backgroundColor: AppColors.surfaceContainerHigh,
        backgroundImage: NetworkImage(url!),
        onBackgroundImageError: (_, __) {},
        child: url!.isEmpty ? Text(initials) : null,
      );
    }

    return CircleAvatar(
      radius: 20,
      backgroundColor: AppColors.primaryContainer,
      child: Text(
        initials,
        style: const TextStyle(
          color: AppColors.primary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
