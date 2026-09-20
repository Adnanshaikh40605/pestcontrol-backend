import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_native_splash/flutter_native_splash.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/app_update_provider.dart';
import '../../providers/auth_provider.dart';

/// Max time splash may block before navigating to home/login destination.
const Duration _kSplashDeadline = Duration(seconds: 5);

/// Matches native Android/iOS splash (white + official logo) so users never see
/// a second, different splash design after launch.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool _navigated = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      FlutterNativeSplash.remove();
    });
    unawaited(_boot());
  }

  Future<void> _boot() async {
    final auth = context.read<AuthProvider>();
    final appUpdate = context.read<AppUpdateProvider>();

    try {
      // Auth restore only — never block splash on Play Store / network hangs.
      await auth.bootstrap().timeout(_kSplashDeadline);
    } catch (e, stack) {
      debugPrint('[Splash] boot error: $e\n$stack');
      // Ensure router redirect can leave /splash even if bootstrap hung.
      if (!auth.ready) {
        auth.markReadyAsGuest();
      }
    }

    _goNext(auth);

    // Play in-app update after navigation so a hung Play API never traps users.
    unawaited(appUpdate.checkForUpdate(silent: true));
  }

  void _goNext(AuthProvider auth) {
    if (!mounted || _navigated) return;
    _navigated = true;
    if (!auth.loggedIn) {
      context.go('/home');
      return;
    }
    context.go(auth.takePendingRoute() ?? '/home');
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
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: const LinearProgressIndicator(
                minHeight: 3,
                backgroundColor: Color(0xFFE8F5E9),
                color: AppColors.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
