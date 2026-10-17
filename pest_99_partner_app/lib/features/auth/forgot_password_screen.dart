import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/user_error.dart';
import '../../services/auth_service.dart';
import '../../shared/widgets/app_snackbar.dart';
import '../../shared/widgets/app_text_field.dart';
import '../../shared/widgets/pest_logo.dart';
import '../../shared/widgets/primary_button.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _mobile = TextEditingController();
  final _otp = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  bool _otpSent = false;
  bool _busy = false;
  int _resendIn = 0;
  Timer? _resendTimer;
  String? _devOtp;

  @override
  void dispose() {
    _resendTimer?.cancel();
    _mobile.dispose();
    _otp.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  void _startResendCooldown() {
    _resendTimer?.cancel();
    setState(() => _resendIn = 30);
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_resendIn <= 1) {
        timer.cancel();
        setState(() => _resendIn = 0);
      } else {
        setState(() => _resendIn -= 1);
      }
    });
  }

  Future<void> _sendOtp() async {
    final mobile = _mobile.text.trim();
    if (mobile.replaceAll(RegExp(r'\D'), '').length < 10) {
      AppSnackBar.error(context, 'Enter your 10-digit mobile number.');
      return;
    }
    setState(() => _busy = true);
    try {
      final data = await AuthService(context.read<ApiClient>()).sendPasswordOtp(mobile);
      if (!mounted) return;
      final dev = data['dev_otp']?.toString();
      setState(() {
        _otpSent = true;
        _devOtp = (dev == null || dev.isEmpty || dev == 'null') ? null : dev;
      });
      _startResendCooldown();
      AppSnackBar.success(context, 'OTP sent to your WhatsApp number.');
    } catch (e) {
      if (!mounted) return;
      AppSnackBar.error(context, userErrorMessage(e, fallback: 'Could not send OTP.'));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reset() async {
    final otp = _otp.text.replaceAll(RegExp(r'\D'), '');
    if (otp.length != 4) {
      AppSnackBar.error(context, 'Enter the 4-digit OTP.');
      return;
    }
    if (_password.text.length < 6) {
      AppSnackBar.error(context, 'Password must be at least 6 characters.');
      return;
    }
    if (_password.text != _confirm.text) {
      AppSnackBar.error(context, 'Passwords do not match.');
      return;
    }
    setState(() => _busy = true);
    try {
      await AuthService(context.read<ApiClient>()).resetPassword(
            mobile: _mobile.text.trim(),
            otp: otp,
            newPassword: _password.text,
          );
      if (!mounted) return;
      AppSnackBar.success(context, 'Password updated. Log in with the new password.');
      context.go('/login');
    } catch (e) {
      if (!mounted) return;
      AppSnackBar.error(context, userErrorMessage(e, fallback: 'Could not update password.'));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.screenEdge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  onPressed: _busy ? null : () => context.go('/login'),
                  child: const Text('Back to login'),
                ),
              ),
              const PestLogo(height: 56),
              const SizedBox(height: 24),
              Text('Reset password', style: Theme.of(context).textTheme.headlineLarge),
              const SizedBox(height: 8),
              Text(
                _otpSent
                    ? 'Enter the OTP from WhatsApp and choose a new password.'
                    : 'We will send a 4-digit OTP to the WhatsApp number on your account.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
              ),
              const SizedBox(height: 32),
              AppTextField(
                label: 'Phone Number',
                hint: 'Enter your phone number',
                keyboardType: TextInputType.phone,
                controller: _mobile,
              ),
              if (_otpSent) ...[
                const SizedBox(height: AppSpacing.sectionGap),
                AppTextField(
                  label: 'OTP',
                  hint: '4-digit OTP',
                  keyboardType: TextInputType.number,
                  controller: _otp,
                ),
                if (_devOtp != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Local test OTP: $_devOtp',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
                const SizedBox(height: AppSpacing.sectionGap),
                AppTextField(
                  label: 'New password',
                  hint: 'At least 6 characters',
                  obscureText: true,
                  controller: _password,
                ),
                const SizedBox(height: AppSpacing.sectionGap),
                AppTextField(
                  label: 'Confirm password',
                  hint: 'Re-enter the new password',
                  obscureText: true,
                  controller: _confirm,
                ),
              ],
              const SizedBox(height: AppSpacing.sectionGap),
              PrimaryButton(
                label: _busy
                    ? 'Please wait…'
                    : _otpSent
                        ? 'Update password'
                        : 'Send OTP',
                onPressed: _busy ? null : (_otpSent ? _reset : _sendOtp),
              ),
              if (_otpSent) ...[
                const SizedBox(height: 12),
                TextButton(
                  onPressed: (_busy || _resendIn > 0) ? null : _sendOtp,
                  child: Text(_resendIn > 0 ? 'Resend OTP in ${_resendIn}s' : 'Resend OTP'),
                ),
              ],
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
