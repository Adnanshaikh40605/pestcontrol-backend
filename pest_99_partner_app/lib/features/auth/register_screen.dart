import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_spacing.dart';
import '../../providers/auth_provider.dart';
import '../../shared/widgets/app_text_field.dart';
import '../../shared/widgets/pest_logo.dart';
import '../../shared/widgets/primary_button.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _name = TextEditingController();
  final _mobile = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _name.dispose();
    _mobile.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final auth = context.read<AuthProvider>();
    final ok = await auth.register(
      fullName: _name.text.trim(),
      mobile: _mobile.text.trim(),
      password: _password.text,
    );
    if (!mounted) return;
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Registered! Wait for CRM approval, then log in.'),
        ),
      );
      context.go('/login');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(auth.error ?? 'Registration failed')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 16),
            const PestLogo(height: 64),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.screenEdge,
                  24,
                  AppSpacing.screenEdge,
                  120,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Create Account', style: Theme.of(context).textTheme.headlineLarge),
                    const SizedBox(height: 4),
                    Text(
                      'Register as a field technician. Admin will approve your app access on CRM.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                          ),
                    ),
                    const SizedBox(height: AppSpacing.sectionGap),
                    AppTextField(
                      label: 'Full Name',
                      hint: 'Enter your full name',
                      controller: _name,
                    ),
                    const SizedBox(height: AppSpacing.elementGap),
                    AppTextField(
                      label: 'Mobile Number',
                      hint: '10 digit mobile number',
                      keyboardType: TextInputType.phone,
                      controller: _mobile,
                    ),
                    const SizedBox(height: AppSpacing.elementGap),
                    AppTextField(
                      label: 'Password',
                      hint: 'Create a strong password',
                      obscureText: true,
                      controller: _password,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: Container(
        padding: EdgeInsets.fromLTRB(
          AppSpacing.screenEdge,
          16,
          AppSpacing.screenEdge,
          MediaQuery.paddingOf(context).bottom + 16,
        ),
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor.withValues(alpha: 0.9),
          border: const Border(top: BorderSide(color: Color(0x80E4E7EC))),
        ),
        child: PrimaryButton(
          label: auth.loading ? 'Creating…' : 'Create Account',
          onPressed: auth.loading ? null : _submit,
        ),
      ),
    );
  }
}
