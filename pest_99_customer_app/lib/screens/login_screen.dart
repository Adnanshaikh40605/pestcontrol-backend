import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';
import '../shared/widgets/legal_footer_links.dart';
import '../shared/widgets/pc99_widgets.dart';

/// Login — mobile number only, then 4-digit OTP.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _mobile = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _mobile.dispose();
    super.dispose();
  }

  Future<void> _sendOtp() async {
    final mobile = _mobile.text.replaceAll(RegExp(r'\D'), '');
    if (mobile.length != 10) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid 10-digit mobile number'), backgroundColor: AppColors.danger),
      );
      return;
    }
    setState(() => _busy = true);
    final result = await context.read<AuthProvider>().sendOtp(mobile: mobile, purpose: 'login');
    if (!mounted) return;
    setState(() => _busy = false);
    if (!result.ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result.error ?? 'Could not send OTP'), backgroundColor: AppColors.danger),
      );
      return;
    }
    if (kDebugMode && result.devOtp != null && result.devOtp!.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('OTP sent · use ${result.devOtp} to verify'), backgroundColor: AppColors.primary),
      );
    }
    context.push('/otp', extra: {
      'mobile': mobile,
      'purpose': 'login',
      'devOtp': result.devOtp,
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Center(child: Pc99Logo(height: 78)),
              const SizedBox(height: 10),
              const Center(
                child: Text(
                  'SAFE · ECO-FRIENDLY · TRUSTED EXPERTS',
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.4,
                    color: AppColors.textMuted,
                  ),
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                'Welcome Back!',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 6),
              const Text(
                'Enter your mobile number to login with OTP',
                style: TextStyle(fontSize: 14, color: AppColors.textMuted),
              ),
              const SizedBox(height: 28),
              Container(
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 14),
                      child: Text('+91', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                    ),
                    Container(width: 1, height: 28, color: AppColors.border),
                    Expanded(
                      child: TextField(
                        controller: _mobile,
                        keyboardType: TextInputType.phone,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(10),
                        ],
                        decoration: const InputDecoration(
                          hintText: 'Enter Mobile Number',
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 16),
                          hintStyle: TextStyle(color: AppColors.textMuted, fontWeight: FontWeight.w400),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              Pc99PrimaryButton(label: 'Send OTP', onPressed: _sendOtp, busy: _busy),
              const Spacer(),
              Center(
                child: TextButton(
                  onPressed: () => context.push('/register'),
                  child: const Text.rich(
                    TextSpan(
                      text: 'New here? ',
                      style: TextStyle(color: AppColors.textMuted),
                      children: [
                        TextSpan(
                          text: 'Create account',
                          style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              const LegalFooterLinks(),
            ],
          ),
        ),
      ),
    );
  }
}

/// 4-digit OTP verification — no password.
class OtpVerifyScreen extends StatefulWidget {
  const OtpVerifyScreen({
    super.key,
    required this.mobile,
    this.purpose = 'login',
    this.fullName = '',
    this.devOtp,
  });

  final String mobile;
  final String purpose;
  final String fullName;
  final String? devOtp;

  @override
  State<OtpVerifyScreen> createState() => _OtpVerifyScreenState();
}

class _OtpVerifyScreenState extends State<OtpVerifyScreen> {
  final _digits = List.generate(4, (_) => TextEditingController());
  final _focus = List.generate(4, (_) => FocusNode());
  bool _busy = false;

  @override
  void dispose() {
    for (final c in _digits) {
      c.dispose();
    }
    for (final f in _focus) {
      f.dispose();
    }
    super.dispose();
  }

  String get _otp => _digits.map((c) => c.text).join();

  Future<void> _verify() async {
    if (_otp.length != 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter the 4-digit OTP'), backgroundColor: AppColors.danger),
      );
      return;
    }
    setState(() => _busy = true);
    final ok = await context.read<AuthProvider>().verifyOtp(
          mobile: widget.mobile,
          otp: _otp,
          purpose: widget.purpose,
          fullName: widget.fullName,
        );
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) {
      final next = context.read<AuthProvider>().takePendingRoute();
      context.go(next ?? '/home');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.read<AuthProvider>().error ?? 'Invalid OTP'),
          backgroundColor: AppColors.danger,
        ),
      );
    }
  }

  Future<void> _resend() async {
    setState(() => _busy = true);
    final result = await context.read<AuthProvider>().sendOtp(
          mobile: widget.mobile,
          purpose: widget.purpose,
          fullName: widget.fullName,
        );
    if (!mounted) return;
    setState(() => _busy = false);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          result.ok
              ? (kDebugMode && result.devOtp != null ? 'OTP resent · use ${result.devOtp}' : 'OTP resent successfully')
              : (result.error ?? 'Could not resend OTP'),
        ),
        backgroundColor: result.ok ? AppColors.primary : AppColors.danger,
      ),
    );
  }

  void _onDigit(int index, String value) {
    if (value.length > 1) {
      // Paste support
      final digits = value.replaceAll(RegExp(r'\D'), '');
      for (var i = 0; i < 4; i++) {
        _digits[i].text = i < digits.length ? digits[i] : '';
      }
      if (digits.length >= 4) {
        _focus[3].unfocus();
        _verify();
      } else if (digits.isNotEmpty) {
        _focus[digits.length.clamp(0, 3)].requestFocus();
      }
      return;
    }
    if (value.isNotEmpty && index < 3) {
      _focus[index + 1].requestFocus();
    }
    if (_otp.length == 4) {
      _verify();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              IconButton(
                onPressed: () => context.pop(),
                padding: EdgeInsets.zero,
                alignment: Alignment.centerLeft,
                icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18, color: AppColors.primary),
              ),
              const SizedBox(height: 8),
              const Center(child: Pc99Logo(height: 56)),
              const SizedBox(height: 22),
              const Text('Enter OTP', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              Text(
                'We sent a 4-digit code to +91 ${widget.mobile}',
                style: const TextStyle(color: AppColors.textMuted, fontSize: 14),
              ),
              if (kDebugMode && widget.devOtp != null && widget.devOtp!.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  'Test OTP: ${widget.devOtp}',
                  style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700, fontSize: 13),
                ),
              ],
              const SizedBox(height: 28),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: List.generate(4, (i) {
                  return SizedBox(
                    width: 64,
                    height: 64,
                    child: TextField(
                      controller: _digits[i],
                      focusNode: _focus[i],
                      keyboardType: TextInputType.number,
                      textAlign: TextAlign.center,
                      maxLength: 4,
                      style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      decoration: InputDecoration(
                        counterText: '',
                        filled: true,
                        fillColor: AppColors.surface,
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: const BorderSide(color: AppColors.border),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: const BorderSide(color: AppColors.primary, width: 1.6),
                        ),
                      ),
                      onChanged: (v) => _onDigit(i, v),
                      onTap: () => _digits[i].selection = TextSelection(baseOffset: 0, extentOffset: _digits[i].text.length),
                    ),
                  );
                }),
              ),
              const SizedBox(height: 24),
              Pc99PrimaryButton(label: 'Verify & Continue', onPressed: _verify, busy: _busy),
              const SizedBox(height: 12),
              Center(
                child: TextButton(
                  onPressed: _busy ? null : _resend,
                  child: const Text('Resend OTP', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
