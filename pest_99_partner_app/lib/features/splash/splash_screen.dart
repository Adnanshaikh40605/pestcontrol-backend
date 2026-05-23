import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../services/profile_service.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/auth_provider.dart';
import '../../providers/notifications_provider.dart';
import '../../providers/profile_provider.dart';
import '../../services/push_notification_service.dart';
import '../../shared/widgets/pest_logo.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    final auth = context.read<AuthProvider>();
    if (!auth.ready) await auth.init();
    if (!mounted) return;
    if (auth.loggedIn) {
      try {
        final data = await ProfileService(context.read<ApiClient>()).getProfile();
        await auth.refreshApprovalFromProfile(data);
        await PushNotificationService.instance.ensureTokenSyncedWithBackend();
        if (mounted) {
          await context.read<ProfileProvider>().loadProfile(force: true);
          await context.read<NotificationsProvider>().load(force: true);
        }
      } catch (_) {
        /* offline or expired */
      }
      PushNotificationService.instance.processPendingNavigation();
    }
    if (!mounted) return;
    if (!auth.loggedIn) {
      context.go('/login');
    } else if (!auth.appApproved) {
      context.go('/pending-approval');
    } else {
      context.go('/bookings');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.primary,
      body: SafeArea(
        child: Stack(
          children: [
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 256,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x33000000),
                          blurRadius: 24,
                          offset: Offset(0, 8),
                        ),
                      ],
                    ),
                    child: const PestLogo(height: 120),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Pest 99',
                    style: Theme.of(context).textTheme.displayLarge,
                  ),
                ],
              ),
            ),
            Positioned(
              left: AppSpacing.screenEdge,
              right: AppSpacing.screenEdge,
              bottom: 48,
              child: Column(
                children: [
                  const SizedBox(
                    width: 160,
                    height: 6,
                    child: LinearProgressIndicator(
                      backgroundColor: Color(0x4DFFFFFF),
                      color: AppColors.onPrimary,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'LOADING OPERATIONS',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: AppColors.onPrimary.withValues(alpha: 0.8),
                          letterSpacing: 3,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
