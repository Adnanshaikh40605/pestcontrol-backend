import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_native_splash/flutter_native_splash.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/app_update_provider.dart';
import '../../providers/auth_provider.dart';

/// Absolute max time on splash before forced navigation (belt + suspenders).
const Duration _kSplashHardDeadline = Duration(seconds: 3);

/// Soft budget for local session restore only (no network).
const Duration _kBootstrapBudget = Duration(seconds: 2);

/// Matches native Android/iOS splash (white + official logo) so users never see
/// a second, different splash design after launch.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool _navigated = false;
  Timer? _hardDeadline;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      FlutterNativeSplash.remove();
    });
    // Hard timer: leave splash even if every await hangs forever.
    _hardDeadline = Timer(_kSplashHardDeadline, _forceLeave);
    unawaited(_boot());
  }

  @override
  void dispose() {
    _hardDeadline?.cancel();
    super.dispose();
  }

  void _forceLeave() {
    if (!mounted || _navigated) return;
    final auth = context.read<AuthProvider>();
    if (!auth.ready) {
      auth.markReadyAsGuest();
    }
    _goNext(auth);
  }

  Future<void> _boot() async {
    final auth = context.read<AuthProvider>();
    final appUpdate = context.read<AppUpdateProvider>();

    try {
      // Local token check only — profile / Play update never block splash.
      await auth.bootstrap().timeout(_kBootstrapBudget);
    } catch (e, stack) {
      debugPrint('[Splash] boot error: $e\n$stack');
      if (!auth.ready) {
        auth.markReadyAsGuest();
      }
    }

    _goNext(auth);

    // After leave — Play update must never gate home.
    unawaited(appUpdate.checkForUpdate(silent: true));
  }

  void _goNext(AuthProvider auth) {
    if (!mounted || _navigated) return;
    _navigated = true;
    _hardDeadline?.cancel();
    final dest = auth.loggedIn ? (auth.takePendingRoute() ?? '/home') : '/home';
    try {
      context.go(dest);
    } catch (e, stack) {
      debugPrint('[Splash] navigate failed: $e\n$stack');
      // Last resort — try home without pending route.
      if (mounted) {
        context.go('/home');
      }
    }
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
