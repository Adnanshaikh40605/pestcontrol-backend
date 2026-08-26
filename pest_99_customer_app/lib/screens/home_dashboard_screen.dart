import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/auth_gate.dart';
import '../core/theme/app_colors.dart';
import '../models/customer_models.dart';
import '../providers/auth_provider.dart';
import '../services/customer_services.dart';
import '../shared/widgets/pc99_widgets.dart';

/// Screen 3 — Home Dashboard (guest-friendly).
class HomeDashboardScreen extends StatefulWidget {
  const HomeDashboardScreen({super.key});

  @override
  State<HomeDashboardScreen> createState() => _HomeDashboardScreenState();
}

class _HomeDashboardScreenState extends State<HomeDashboardScreen> {
  List<CustomerBooking> _bookings = [];
  List<AmcScheduleGroup> _amc = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final auth = context.read<AuthProvider>();
    if (!auth.loggedIn) {
      if (mounted) {
        setState(() {
          _bookings = [];
          _amc = [];
          _loading = false;
        });
      }
      return;
    }
    try {
      final api = context.read<ApiClient>();
      final svc = BookingService(api);
      final bookings = await svc.list();
      List<AmcScheduleGroup> amc = const [];
      try {
        amc = await svc.amcSchedule();
      } catch (_) {}
      if (!mounted) return;
      setState(() {
        _bookings = bookings;
        _amc = amc;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final profile = auth.profile;
    final name = profile?.fullName.split(' ').first ?? 'Guest';
    final hour = DateTime.now().hour;
    final greet = hour < 12 ? 'Good Morning!' : (hour < 17 ? 'Good Afternoon!' : 'Good Evening!');
    final next = _bookings.where((b) => !b.isDone).cast<CustomerBooking?>().firstWhere((_) => true, orElse: () => null);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.primary,
          onRefresh: _load,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 4),
                child: Center(child: Pc99Logo(height: 40)),
              ),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Stack(
                  children: [
                    Positioned(
                      right: -6,
                      top: -4,
                      child: Icon(Icons.settings_suggest_outlined, size: 72, color: Colors.white.withValues(alpha: 0.12)),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Hello, $name',
                          style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 2),
                        Text(greet, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12)),
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.verified_user_outlined, color: Colors.white, size: 14),
                              SizedBox(width: 4),
                              Text(
                                'Safe & Certified Pest Control',
                                style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              if (_loading)
                const LinearProgressIndicator(minHeight: 2, color: AppColors.primary)
              else if (!auth.loggedIn) ...[
                Pc99EmptyBookPrompt(
                  title: 'Book pest control',
                  subtitle: 'Sign in to browse services and book pest control.',
                  onBook: () => pushAuthed(context, '/book/property'),
                ),
              ] else if (next == null && _amc.isEmpty) ...[
                Pc99EmptyBookPrompt(
                  title: 'Book your first service',
                  subtitle: 'No bookings yet. Schedule pest control for your property.',
                  onBook: () => pushAuthed(context, '/book/property'),
                ),
              ] else ...[
                const Pc99SectionTitle('Next Service Due'),
                const SizedBox(height: 10),
                Pc99Card(
                  child: Column(
                    children: [
                      Row(
                        children: [
                          const Pc99IconBubble(icon: Icons.pest_control_outlined),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  next?.serviceType ?? '${_amc.first.parent.serviceType} AMC',
                                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                                ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(Icons.calendar_today_outlined, size: 13, color: AppColors.textMuted),
                                    const SizedBox(width: 5),
                                    Text(
                                      next?.scheduleDatetime != null
                                          ? 'Due on ${DateFormat('d MMM yyyy').format(DateTime.parse(next!.scheduleDatetime!).toLocal())}'
                                          : 'Schedule your next visit',
                                      style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(
                            child: SizedBox(
                              height: 42,
                              child: ElevatedButton(
                                onPressed: () => pushAuthed(context, '/book/property'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppColors.primary,
                                  foregroundColor: Colors.white,
                                  elevation: 0,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                                child: const Text('Book Now', style: TextStyle(fontWeight: FontWeight.w700)),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: SizedBox(
                              height: 42,
                              child: OutlinedButton(
                                onPressed: () => pushAuthed(context, '/book/property'),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: AppColors.primary,
                                  side: const BorderSide(color: AppColors.primary),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                                child: const Text('Book Early', style: TextStyle(fontWeight: FontWeight.w700)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 16),
              const Pc99SectionTitle('Quick Actions'),
              const SizedBox(height: 10),
              GridView.count(
                crossAxisCount: 4,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 10,
                crossAxisSpacing: 8,
                childAspectRatio: 0.88,
                children: [
                  _QA(Icons.calendar_month_outlined, 'Book', () => pushAuthed(context, '/book/property')),
                  _QA(Icons.workspace_premium_outlined, 'My AMC', () => goAuthed(context, '/amc')),
                  _QA(Icons.support_agent_rounded, 'Complaint', () => pushAuthed(context, '/complaint')),
                  _QA(Icons.receipt_long_outlined, 'Payments', () => goAuthed(context, '/payments')),
                  _QA(Icons.event_note_outlined, 'Bookings', () => goAuthed(context, '/bookings')),
                  _QA(Icons.description_outlined, 'Reports', () => pushAuthed(context, '/report')),
                  _QA(Icons.person_outline_rounded, 'Account', () => goAuthed(context, '/account')),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QA extends StatelessWidget {
  const _QA(this.icon, this.label, this.onTap);
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Column(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: Icon(icon, color: AppColors.primary, size: 20),
          ),
          const SizedBox(height: 5),
          Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
