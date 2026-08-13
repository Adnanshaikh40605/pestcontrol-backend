import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';
import '../shared/widgets/legal_footer_links.dart';
import '../shared/widgets/pc99_widgets.dart';

/// Register — name + mobile only, then OTP (no password).
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _name = TextEditingController();
  final _mobile = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _mobile.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _name.text.trim();
    final mobile = _mobile.text.trim();
    if (name.length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your name'), backgroundColor: AppColors.danger),
      );
      return;
    }
    if (mobile.length != 10) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid 10-digit mobile number'), backgroundColor: AppColors.danger),
      );
      return;
    }

    setState(() => _busy = true);
    final result = await context.read<AuthProvider>().sendOtp(
          mobile: mobile,
          purpose: 'register',
          fullName: name,
        );
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
      'purpose': 'register',
      'fullName': name,
      'devOtp': result.devOtp,
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          children: [
            IconButton(
              onPressed: () => context.pop(),
              padding: EdgeInsets.zero,
              alignment: Alignment.centerLeft,
              icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18, color: AppColors.primary),
            ),
            const SizedBox(height: 8),
            const Center(child: Pc99Logo(height: 64)),
            const SizedBox(height: 22),
            const Text(
              'Create account',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            const Text(
              'Enter your name and mobile number — no password needed',
              style: TextStyle(fontSize: 14, color: AppColors.textMuted),
            ),
            const SizedBox(height: 28),
            TextField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              decoration: InputDecoration(
                labelText: 'Full name',
                hintText: 'Your name',
                filled: true,
                fillColor: AppColors.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _mobile,
              keyboardType: TextInputType.phone,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(10),
              ],
              decoration: InputDecoration(
                labelText: 'Mobile number',
                hintText: '10-digit mobile',
                prefixText: '+91  ',
                filled: true,
                fillColor: AppColors.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
            const SizedBox(height: 24),
            Pc99PrimaryButton(label: 'Send OTP', onPressed: _submit, busy: _busy),
            const SizedBox(height: 12),
            Center(
              child: TextButton(
                onPressed: () => context.go('/login'),
                child: const Text.rich(
                  TextSpan(
                    text: 'Already have an account? ',
                    style: TextStyle(color: AppColors.textMuted),
                    children: [
                      TextSpan(
                        text: 'Login',
                        style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            const LegalFooterLinks(),
          ],
        ),
      ),
    );
  }
}
