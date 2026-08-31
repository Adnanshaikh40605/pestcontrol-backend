import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_native_splash/flutter_native_splash.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../providers/app_update_provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/profile_provider.dart';
import '../../services/profile_service.dart';
import '../../services/push_notification_service.dart';

/// Matches the native Android/iOS splash (white + official logo) so the handoff
/// from OS splash → Flutter has no visible second design.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      FlutterNativeSplash.remove();
    });
    _boot();
  }

  Future<void> _boot() async {
    try {
      // Native Play Store update prompt when a newer release is live.
      await context.read<AppUpdateProvider>().checkForUpdate();
      if (!mounted) return;

      final auth = context.read<AuthProvider>();
      await auth.init();
      if (!mounted) return;

      _navigateForSession(auth);
      unawaited(_warmSessionInBackground(auth));
    } catch (e, stack) {
      debugPrint('[Splash] boot error: $e\n$stack');
      if (!mounted) return;
      final auth = context.read<AuthProvider>();
      if (!auth.ready) await auth.init();
      if (!mounted) return;
      _navigateForSession(auth);
    }
  }

  void _navigateForSession(AuthProvider auth) {
    if (!auth.loggedIn) {
      context.go('/login');
      return;
    }
    if (!auth.appApproved) {
      context.go('/pending-approval');
      return;
    }
    context.go('/bookings');
    PushNotificationService.instance.processPendingNavigation();
  }

  Future<void> _warmSessionInBackground(AuthProvider auth) async {
    if (!auth.loggedIn) return;

    await auth.warmSessionAfterLogin();
    if (!mounted) return;

    try {
      final data = await ProfileService(context.read<ApiClient>())
          .getProfile()
          .timeout(const Duration(seconds: 12));
      await auth.refreshApprovalFromProfile(data);
    } catch (_) {
      /* offline or expired — router/auth redirect will handle */
    }

    if (!mounted) return;
    if (!auth.loggedIn || !auth.appApproved) return;

    unawaited(context.read<ProfileProvider>().loadProfile(force: true));
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.dark.copyWith(
        statusBarColor: Colors.transparent,
        systemNavigationBarColor: Colors.white,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
      child: const Scaffold(
        backgroundColor: Colors.white,
        body: BrandSplashBody(),
      ),
    );
  }
}

/// Shared splash body — keep identical to Customer app.
class BrandSplashBody extends StatelessWidget {
  const BrandSplashBody({super.key});

  static const String logoAsset = 'assets/logo/splash_logo.png';

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final logoWidth = (width * 0.72).clamp(220.0, 320.0);

    return SafeArea(
      child: Stack(
        children: [
          Center(
            child: Image.asset(
              logoAsset,
              width: logoWidth,
              fit: BoxFit.contain,
              filterQuality: FilterQuality.high,
            ),
          ),
          Positioned(
            left: 40,
            right: 40,
            bottom: 48,
            child: Column(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: const LinearProgressIndicator(
                    minHeight: 3,
                    backgroundColor: Color(0xFFE8F5EC),
                    color: AppColors.primary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
