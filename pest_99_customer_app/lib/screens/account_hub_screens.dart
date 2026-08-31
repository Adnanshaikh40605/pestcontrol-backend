import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../config/legal_config.dart';
import '../core/api_client.dart';
import '../core/auth_gate.dart';
import '../core/theme/app_colors.dart';
import '../models/customer_models.dart';
import '../providers/auth_provider.dart';
import '../providers/booking_flow_provider.dart';
import '../services/customer_services.dart';
import '../shared/widgets/legal_footer_links.dart';
import '../shared/widgets/pc99_widgets.dart';

/// Screen 11 — My AMC Dashboard
class AmcDashboardScreen extends StatefulWidget {
  const AmcDashboardScreen({super.key});

  @override
  State<AmcDashboardScreen> createState() => _AmcDashboardScreenState();
}

class _AmcDashboardScreenState extends State<AmcDashboardScreen> {
  int tab = 0;
  List<AmcScheduleGroup> _amc = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final list = await BookingService(context.read<ApiClient>()).amcSchedule();
      if (!mounted) return;
      setState(() {
        _amc = list;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _amc = [];
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final active = _amc;
    final expired = <AmcScheduleGroup>[]; // API currently returns active schedule groups

    return Pc99Scaffold(
      title: 'My AMC Dashboard',
      onBack: () => context.canPop() ? context.pop() : context.go('/home'),
      child: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : Column(
              children: [
                if (active.isNotEmpty || expired.isNotEmpty)
                  Row(
                    children: [
                      Expanded(
                        child: _Tab(
                          label: 'Active (${active.length})',
                          selected: tab == 0,
                          onTap: () => setState(() => tab = 0),
                        ),
                      ),
                      Expanded(
                        child: _Tab(
                          label: 'Expired (${expired.length})',
                          selected: tab == 1,
                          onTap: () => setState(() => tab = 1),
                        ),
                      ),
                    ],
                  ),
                Expanded(
                  child: active.isEmpty && expired.isEmpty
                      ? Pc99EmptyBookPrompt(
                          title: 'No AMC plans yet',
                          subtitle: 'You don’t have an active AMC. Book a service and choose the AMC package to protect your property year-round.',
                          buttonLabel: 'Book AMC Service',
                          onBook: () => pushAuthed(context, '/book/property'),
                        )
                      : RefreshIndicator(
                          color: AppColors.primary,
                          onRefresh: _load,
                          child: ListView(
                            padding: const EdgeInsets.all(16),
                            children: tab == 1
                                ? [
                                    if (expired.isEmpty)
                                      const Padding(
                                        padding: EdgeInsets.only(top: 48),
                                        child: Center(
                                          child: Text('No expired AMC plans', style: TextStyle(color: AppColors.textMuted)),
                                        ),
                                      )
                                    else
                                      ...expired.map((g) => _buildCard(g)),
                                  ]
                                : active.map(_buildCard).toList(),
                          ),
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildCard(AmcScheduleGroup g) {
    final visits = g.visits;
    final completed = visits.where((v) => v.isDone).length;
    final remaining = (visits.length - completed).clamp(0, 999);
    final next = visits.where((v) => !v.isDone).cast<CustomerBooking?>().firstWhere((_) => true, orElse: () => null);
    String nextDue = '—';
    if (next?.scheduleDatetime != null) {
      try {
        nextDue = DateFormat('d MMM yyyy').format(DateTime.parse(next!.scheduleDatetime!).toLocal());
      } catch (_) {
        nextDue = next!.scheduleDatetime!;
      }
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: _AmcCard(
        title: g.parent.serviceType,
        location: g.parent.bhkSize?.isNotEmpty == true
            ? '${g.parent.propertyType ?? 'Home'} • ${g.parent.bhkSize}'
            : (g.parent.propertyType ?? 'AMC Plan'),
        badge: 'AMC',
        start: '—',
        end: '—',
        total: visits.isEmpty ? 1 : visits.length,
        completed: completed,
        remaining: remaining,
        nextDue: nextDue,
        onTap: () => context.push('/amc/${g.parent.id}'),
      ),
    );
  }
}

class _Tab extends StatelessWidget {
  const _Tab({required this.label, required this.selected, required this.onTap});
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: selected ? AppColors.primary : AppColors.border, width: selected ? 2.5 : 1),
          ),
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: selected ? AppColors.primary : AppColors.textMuted,
            fontWeight: FontWeight.w700,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}

class _AmcCard extends StatelessWidget {
  const _AmcCard({
    required this.title,
    required this.location,
    required this.badge,
    required this.start,
    required this.end,
    required this.total,
    required this.completed,
    required this.remaining,
    required this.nextDue,
    required this.onTap,
  });

  final String title;
  final String location;
  final String badge;
  final String start;
  final String end;
  final int total;
  final int completed;
  final int remaining;
  final String nextDue;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pc99Card(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                    const SizedBox(height: 3),
                    Text(location, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.successBg,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(badge, style: const TextStyle(color: AppColors.primary, fontSize: 10, fontWeight: FontWeight.w800)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _Metric(label: 'Total', value: '$total'),
              _Metric(label: 'Done', value: '$completed'),
              _Metric(label: 'Left', value: '$remaining'),
            ],
          ),
          const SizedBox(height: 10),
          Text('Next due: $nextDue', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
        ],
      ),
    );
  }
}

/// Screen 13 — Complaint / Re-Service
class ComplaintScreen extends StatefulWidget {
  const ComplaintScreen({super.key});

  @override
  State<ComplaintScreen> createState() => _ComplaintScreenState();
}

class _ComplaintScreenState extends State<ComplaintScreen> {
  String? _type;
  final _note = TextEditingController();
  bool _busy = false;

  static const _options = [
    ('Service not effective', 'Pests returned after treatment'),
    ('Technician behaviour', 'Report an issue with visit'),
    ('Request re-service', 'Book a free follow-up visit'),
  ];

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_type == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select a complaint type'), backgroundColor: AppColors.danger),
      );
      return;
    }
    if (_note.text.trim().length < 5) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please describe the issue'), backgroundColor: AppColors.danger),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await SupportService(context.read<ApiClient>()).submitComplaint(
        complaintType: _type!,
        note: _note.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Complaint submitted. Our team will contact you.'),
          backgroundColor: AppColors.primary,
        ),
      );
      context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Pc99Scaffold(
      title: 'Complaint / Re-Service',
      onBack: () => context.pop(),
      floatingBottom: Pc99PrimaryButton(
        label: _busy ? 'Submitting…' : 'Submit Request',
        onPressed: _busy ? null : _submit,
        busy: _busy,
      ),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Pc99SectionTitle('What do you need help with?'),
          const SizedBox(height: 10),
          ..._options.map((opt) {
            final selected = _type == opt.$1;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Pc99Card(
                selected: selected,
                onTap: () => setState(() => _type = opt.$1),
                child: Row(
                  children: [
                    const Pc99IconBubble(icon: Icons.support_agent_rounded),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(opt.$1, style: const TextStyle(fontWeight: FontWeight.w700)),
                          Text(opt.$2, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                        ],
                      ),
                    ),
                    Icon(
                      selected ? Icons.radio_button_checked : Icons.radio_button_off,
                      color: selected ? AppColors.primary : AppColors.border,
                    ),
                  ],
                ),
              ),
            );
          }),
          const SizedBox(height: 16),
          const Pc99SectionTitle('Describe the issue'),
          const SizedBox(height: 8),
          TextField(
            controller: _note,
            maxLines: 4,
            decoration: const InputDecoration(hintText: 'Tell us what happened…'),
          ),
        ],
      ),
    );
  }
}

/// Screen 12 — Service Report
class ServiceReportScreen extends StatelessWidget {
  const ServiceReportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Pc99Scaffold(
      brandTitle: true,
      onBack: () => context.pop(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Pc99SectionTitle('Service Reports'),
          const SizedBox(height: 12),
          Pc99EmptyBookPrompt(
            title: 'No reports yet',
            subtitle: 'After your first completed service, the report will appear here.',
            onBook: () => pushAuthed(context, '/book/property'),
          ),
        ],
      ),
    );
  }
}

/// Screen 15 — Payments & Invoices (bottom Payments tab)
class PaymentsScreen extends StatefulWidget {
  const PaymentsScreen({super.key});

  @override
  State<PaymentsScreen> createState() => _PaymentsScreenState();
}

class _PaymentsScreenState extends State<PaymentsScreen> {
  List<CustomerBooking> _items = [];
  bool _loading = true;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final list = await BookingService(context.read<ApiClient>()).list();
      if (!mounted) return;
      setState(() {
        _items = list;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<CustomerBooking> get _filtered {
    final q = _query.trim().toLowerCase();
    if (q.isEmpty) return _items;
    return _items.where((b) {
      final hay = '${b.serviceType} ${b.code ?? ''} ${b.paymentStatus ?? ''}'.toLowerCase();
      return hay.contains(q);
    }).toList();
  }

  String _amount(CustomerBooking b) {
    final raw = b.invoiceAmount ?? b.price;
    if (raw == null || raw.isEmpty) return '—';
    final n = double.tryParse(raw);
    if (n == null) return '₹$raw';
    return BookingFlowProvider.formatInr(n);
  }

  String _date(CustomerBooking b) {
    final raw = b.scheduleDatetime;
    if (raw == null || raw.isEmpty) return '—';
    try {
      return DateFormat('d MMM yyyy').format(DateTime.parse(raw).toLocal());
    } catch (_) {
      return raw;
    }
  }

  @override
  Widget build(BuildContext context) {
    final rows = _filtered;
    return Pc99Scaffold(
      brandTitle: true,
      onBack: () => context.canPop() ? context.pop() : context.go('/home'),
      child: RefreshIndicator(
        color: AppColors.primary,
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          children: [
            const Text('Payments & Invoices', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            const Text(
              'View your transaction history and invoices.',
              style: TextStyle(color: AppColors.textMuted, fontSize: 13),
            ),
            const SizedBox(height: 14),
            TextField(
              onChanged: (v) => setState(() => _query = v),
              decoration: InputDecoration(
                hintText: 'Search transactions…',
                prefixIcon: const Icon(Icons.search_rounded, color: AppColors.textMuted),
                filled: true,
                fillColor: AppColors.surface,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppColors.border),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppColors.border),
                ),
              ),
            ),
            const SizedBox(height: 14),
            if (_loading)
              const Padding(
                padding: EdgeInsets.only(top: 40),
                child: Center(child: CircularProgressIndicator(color: AppColors.primary)),
              )
            else if (rows.isEmpty)
              Pc99EmptyBookPrompt(
                title: 'No invoices yet',
                subtitle: 'After you book a service, invoices and payments will show up here.',
                onBook: () => pushAuthed(context, '/book/property'),
              )
            else
              ...rows.map((b) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Pc99Card(
                    onTap: () => context.push('/booking/${b.id}'),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                b.serviceType.isEmpty ? 'Pest Control Service' : b.serviceType,
                                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                              ),
                            ),
                            Text(
                              _amount(b),
                              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: AppColors.primary),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(_date(b), style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                        const SizedBox(height: 2),
                        Text(
                          b.code != null && b.code!.isNotEmpty ? b.code! : 'Booking #${b.id}',
                          style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: b.isPaid ? AppColors.successSoft : const Color(0xFFFFF7ED),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                b.paymentStatusLabel,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: b.isPaid ? AppColors.primary : AppColors.warning,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          width: double.infinity,
                          height: 42,
                          child: ElevatedButton.icon(
                            onPressed: () => context.push('/invoice/${b.id}'),
                            icon: const Icon(Icons.download_rounded, size: 18),
                            label: const Text('Download Invoice PDF', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.primary,
                              foregroundColor: Colors.white,
                              elevation: 0,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

/// Screen 16 — Profile & Account
class AccountScreen extends StatelessWidget {
  const AccountScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final profile = auth.profile;
    return Pc99Scaffold(
      brandTitle: true,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              gradient: const LinearGradient(
                colors: [Color(0xFF0A4F16), AppColors.primaryMid],
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 58,
                  height: 58,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.person, color: AppColors.primary, size: 32),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(profile?.fullName ?? 'Customer', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          const Icon(Icons.phone_outlined, color: Colors.white70, size: 13),
                          const SizedBox(width: 4),
                          Text('+91 ${profile?.mobile ?? '—'}', style: const TextStyle(color: Colors.white, fontSize: 12)),
                        ],
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 34,
                  height: 34,
                  decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                  child: const Icon(Icons.edit_outlined, size: 16, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Pc99Card(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                _Menu(Icons.home_work_outlined, 'Book a Service', () => pushAuthed(context, '/book/property')),
                _Menu(Icons.workspace_premium_outlined, 'My AMC', () => context.push('/amc')),
                _Menu(Icons.receipt_long_outlined, 'Payments & Invoices', () => context.push('/payments')),
                _Menu(Icons.support_agent_rounded, 'Complaint / Re-Service', () => context.push('/complaint')),
                _Menu(Icons.help_outline, 'Help & Support', () => openLegalUrl(LegalConfig.contact)),
                _Menu(Icons.privacy_tip_outlined, 'Privacy Policy', () => openLegalUrl(LegalConfig.privacyPolicy)),
                _Menu(Icons.description_outlined, 'Terms & Conditions', () => openLegalUrl(LegalConfig.termsAndConditions)),
                _Menu(Icons.info_outline, 'About Us', () => openLegalUrl(LegalConfig.websiteBase)),
                ListTile(
                  leading: Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppColors.danger.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.delete_forever_outlined, color: AppColors.danger, size: 18),
                  ),
                  title: const Text('Delete account', style: TextStyle(color: AppColors.danger, fontWeight: FontWeight.w700)),
                  onTap: () async {
                    final ok = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('Delete account permanently?'),
                        content: const Text(
                          'This permanently deletes your Pest Control 99 customer account. '
                          'Completed bookings may be retained for legal and billing purposes. '
                          'This cannot be undone.',
                        ),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                          FilledButton(
                            style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
                            onPressed: () => Navigator.pop(ctx, true),
                            child: const Text('Delete'),
                          ),
                        ],
                      ),
                    );
                    if (ok != true || !context.mounted) return;
                    final success = await auth.deleteAccount();
                    if (!context.mounted) return;
                    if (success) {
                      context.go('/login');
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(auth.error ?? 'Could not delete account'), backgroundColor: AppColors.danger),
                      );
                    }
                  },
                ),
                ListTile(
                  leading: Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppColors.danger.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.logout_rounded, color: AppColors.danger, size: 18),
                  ),
                  title: const Text('Logout', style: TextStyle(color: AppColors.danger, fontWeight: FontWeight.w700)),
                  onTap: () async {
                    await auth.logout();
                    if (context.mounted) context.go('/login');
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Menu extends StatelessWidget {
  const _Menu(this.icon, this.label, this.onTap);
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: AppColors.successBg,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: AppColors.primary, size: 18),
      ),
      title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
      trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
      onTap: onTap,
    );
  }
}

/// AMC details — loads real schedule group from API by parent id.
class AmcDetailsScreen extends StatefulWidget {
  const AmcDetailsScreen({super.key, required this.id});
  final String id;

  @override
  State<AmcDetailsScreen> createState() => _AmcDetailsScreenState();
}

class _AmcDetailsScreenState extends State<AmcDetailsScreen> {
  AmcScheduleGroup? _group;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await BookingService(context.read<ApiClient>()).amcSchedule();
      final id = int.tryParse(widget.id);
      AmcScheduleGroup? match;
      for (final g in list) {
        if (g.parent.id == id) {
          match = g;
          break;
        }
      }
      if (!mounted) return;
      setState(() {
        _group = match;
        _loading = false;
        if (match == null) _error = 'AMC plan not found';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '$e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final g = _group;
    final visits = g?.visits ?? const <CustomerBooking>[];
    final completed = visits.where((v) => v.isDone).length;
    final remaining = (visits.length - completed).clamp(0, 999);
    final next = visits.where((v) => !v.isDone).cast<CustomerBooking?>().firstWhere((_) => true, orElse: () => null);
    String nextDue = '—';
    if (next?.scheduleDatetime != null) {
      try {
        nextDue = DateFormat('d MMM yyyy').format(DateTime.parse(next!.scheduleDatetime!).toLocal());
      } catch (_) {
        nextDue = next!.scheduleDatetime!;
      }
    }

    return Pc99Scaffold(
      title: 'AMC Service Details',
      onBack: () => context.pop(),
      floatingBottom: Row(
        children: [
          Expanded(child: Pc99OutlineButton(label: 'Raise Complaint', onPressed: () => context.push('/complaint'))),
          const SizedBox(width: 10),
          Expanded(child: Pc99PrimaryButton(label: 'Book Service', onPressed: () => pushAuthed(context, '/book/property'))),
        ],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textMuted)),
                        const SizedBox(height: 12),
                        TextButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    _AmcCard(
                      title: g!.parent.serviceType,
                      location: g.parent.bhkSize?.isNotEmpty == true
                          ? '${g.parent.propertyType ?? 'Home'} • ${g.parent.bhkSize}'
                          : (g.parent.propertyType ?? 'AMC Plan'),
                      badge: 'AMC',
                      start: '—',
                      end: '—',
                      total: visits.isEmpty ? 1 : visits.length,
                      completed: completed,
                      remaining: remaining,
                      nextDue: nextDue,
                      onTap: () {},
                    ),
                    const SizedBox(height: 16),
                    const Pc99SectionTitle('Service Visits'),
                    const SizedBox(height: 8),
                    if (visits.isEmpty)
                      const Text(
                        'Visit history will appear after your first AMC service.',
                        style: TextStyle(color: AppColors.textMuted, fontSize: 13),
                      )
                    else
                      ...visits.asMap().entries.map((entry) {
                        final idx = entry.key;
                        final v = entry.value;
                        String due = '—';
                        if (v.scheduleDatetime != null) {
                          try {
                            due = DateFormat('d MMM yyyy').format(DateTime.parse(v.scheduleDatetime!).toLocal());
                          } catch (_) {
                            due = v.scheduleDatetime!;
                          }
                        }
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Pc99Card(
                            onTap: () => context.push('/booking/${v.id}'),
                            child: Row(
                              children: [
                                Icon(
                                  v.isDone ? Icons.check_circle : Icons.radio_button_unchecked,
                                  color: v.isDone ? AppColors.primary : AppColors.border,
                                  size: 20,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Visit ${v.serviceCycle ?? (idx + 1)}',
                                        style: const TextStyle(fontWeight: FontWeight.w700),
                                      ),
                                      Text(due, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                                    ],
                                  ),
                                ),
                                Text(
                                  v.status ?? 'Pending',
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                                ),
                              ],
                            ),
                          ),
                        );
                      }),
                  ],
                ),
    );
  }
}
