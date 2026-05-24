import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_spacing.dart';
import '../../providers/auth_provider.dart';
import '../../providers/profile_provider.dart';
import '../../providers/notifications_provider.dart';
import '../../services/push_notification_service.dart';
import '../../shared/widgets/app_text_field.dart';
import '../../shared/widgets/pest_logo.dart';
import '../../shared/widgets/primary_button.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _mobile = TextEditingController();
  final _password = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final auth = context.read<AuthProvider>();
      final msg = auth.sessionExpiredMessage;
      if (msg != null && msg.isNotEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
        auth.clearSessionMessage();
      }
    });
  }

  @override
  void dispose() {
    _mobile.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final auth = context.read<AuthProvider>();
    final ok = await auth.login(_mobile.text.trim(), _password.text);
    if (!mounted) return;
    if (ok) {
      await context.read<ProfileProvider>().loadProfile(force: true);
      if (!mounted) return;
      final approved = context.read<AuthProvider>().appApproved;
      if (approved) {
        await context.read<NotificationsProvider>().load(force: true);
        if (!mounted) return;
        context.go('/bookings');
        PushNotificationService.instance.processPendingNavigation();
      } else {
        context.go('/pending-approval');
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(auth.error ?? 'Login failed')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.screenEdge),
          child: Column(
            children: [
              const SizedBox(height: 24),
              const PestLogoCard(),
              const SizedBox(height: 32),
              Text('Welcome Back', style: Theme.of(context).textTheme.headlineLarge),
              const SizedBox(height: 8),
              Text(
                'Sign in to your partner account',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
              ),
              const SizedBox(height: 40),
              AppTextField(
                label: 'Phone Number',
                hint: 'Enter your phone number',
                keyboardType: TextInputType.phone,
                controller: _mobile,
              ),
              const SizedBox(height: AppSpacing.sectionGap),
              AppTextField(
                label: 'Password',
                hint: 'Enter your password',
                obscureText: true,
                controller: _password,
              ),
              const SizedBox(height: AppSpacing.sectionGap),
              PrimaryButton(
                label: auth.loading ? 'Signing in…' : 'Login',
                onPressed: auth.loading ? null : _submit,
              ),
              const SizedBox(height: 24),
              TextButton(
                onPressed: () => context.push('/register'),
                child: const Text('Create partner account'),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
