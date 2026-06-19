import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../providers/app_providers.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>(() => context.read<TrackingProvider>().refreshStatus());
  }

  @override
  Widget build(BuildContext context) {
    final tracking = context.watch<TrackingProvider>();
    final auth = context.read<AuthProvider>();
    final profile = tracking.me?['profile'] as Map<String, dynamic>?;
    final name = profile?['name']?.toString() ?? 'Staff';
    final hasConsent = tracking.me?['has_consent'] == true;
    final checkedIn = tracking.isCheckedIn;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Today'),
        actions: [
          IconButton(
            onPressed: () async {
              await auth.logout();
              if (context.mounted) context.go('/login');
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: tracking.refreshStatus,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text('Hello, $name', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(
              checkedIn ? 'You are checked in — GPS tracking is active' : 'Check in to start your shift',
              style: TextStyle(color: checkedIn ? Colors.green.shade700 : Colors.grey.shade700),
            ),
            if (tracking.error != null) ...[
              const SizedBox(height: 12),
              Text(tracking.error!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 24),
            if (!hasConsent)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        'GPS Tracking Consent',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Location is recorded only while you are checked in during working hours.',
                      ),
                      const SizedBox(height: 12),
                      FilledButton(
                        onPressed: tracking.isLoading ? null : () => tracking.acceptConsent(),
                        child: const Text('I agree'),
                      ),
                    ],
                  ),
                ),
              ),
            if (hasConsent) ...[
              FilledButton.icon(
                onPressed: tracking.isLoading
                    ? null
                    : () async {
                        if (checkedIn) {
                          await tracking.checkOut();
                        } else {
                          await tracking.checkIn();
                        }
                      },
                icon: Icon(checkedIn ? Icons.logout : Icons.login),
                label: Text(checkedIn ? 'Check out' : 'Check in'),
              ),
            ],
            if (tracking.isLoading) const LinearProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
