import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';
import '../providers/booking_flow_provider.dart';
import '../services/customer_services.dart';
import '../shared/widgets/pc99_widgets.dart';
import 'package:intl/intl.dart';

/// Booking page — Home / Commercial tabs, property configuration,
/// then service selection with per-service "More Options".
class PropertySelectionScreen extends StatefulWidget {
  const PropertySelectionScreen({super.key, this.initialServiceId});

  final String? initialServiceId;

  @override
  State<PropertySelectionScreen> createState() => _PropertySelectionScreenState();
}

class _PropertySelectionScreenState extends State<PropertySelectionScreen> {
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadCatalog();
      _applyInitialService();
    });
  }

  void _applyInitialService() {
    final id = widget.initialServiceId?.trim();
    if (id == null || id.isEmpty) return;
    final flow = context.read<BookingFlowProvider>();
    if (flow.serviceById(id) == null) return;
    flow.selectOnlyService(id);
  }

  Future<void> _loadCatalog() async {
    final flow = context.read<BookingFlowProvider>();
    flow.setRatesLoading(true);
    try {
      final rates = await CatalogService(context.read<ApiClient>()).list();
      if (!mounted) return;
      flow.setRates(rates);
    } catch (e) {
      if (!mounted) return;
      flow.setRatesError('$e');
    }
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  /// Gently scroll down so newly revealed content (services / More Options)
  /// is visible to the user.
  void _nudgeScroll(double delta) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      final target = (_scroll.offset + delta).clamp(0.0, _scroll.position.maxScrollExtent);
      _scroll.animateTo(target, duration: const Duration(milliseconds: 350), curve: Curves.easeOut);
    });
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final canContinue = flow.propertySelected && flow.selectedServiceIds.isNotEmpty;

    return Pc99Scaffold(
      brandTitle: true,
      onBack: () => context.pop(),
      floatingBottom: Pc99PrimaryButton(
        label: 'Continue',
        onPressed: canContinue ? () => context.push('/book/datetime') : null,
      ),
      child: ListView(
        controller: _scroll,
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
        children: [
          const Text('Book Service', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text('Select your property type to get started', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
          if (flow.selectedServiceIds.isNotEmpty) ...[
            const SizedBox(height: 14),
            _PreselectedServiceBanner(flow: flow),
          ],
          const SizedBox(height: 16),
          _CategoryTabs(
            category: flow.propertyCategory,
            onChanged: flow.setCategory,
          ),
          const SizedBox(height: 18),
          Pc99SectionTitle(flow.isHome ? 'Select Property Size' : 'Select Property Type'),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: (flow.isHome
                    ? BookingFlowProvider.homeBhkOptions
                    : BookingFlowProvider.commercialOptions)
                .map((opt) {
              final selected = flow.isHome ? flow.homeBhk == opt : flow.commercialType == opt;
              return _ConfigChip(
                label: opt,
                selected: selected,
                onTap: () {
                  final firstSelection = !flow.propertySelected;
                  if (flow.isHome) {
                    flow.selectHomeBhk(opt);
                  } else {
                    flow.selectCommercialType(opt);
                  }
                  // Reveal the Select Service section that appears below.
                  if (firstSelection && flow.propertySelected) _nudgeScroll(180);
                },
              );
            }).toList(),
          ),
          if ((flow.isHome && flow.homeBhk == 'Custom') ||
              (!flow.isHome && flow.commercialType == 'Other')) ...[
            const SizedBox(height: 12),
            TextFormField(
              initialValue: flow.customConfig,
              onChanged: flow.setCustomConfig,
              keyboardType: flow.isHome ? TextInputType.number : TextInputType.text,
              inputFormatters: flow.isHome
                  ? [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(2)]
                  : null,
              decoration: InputDecoration(
                hintText: flow.isHome
                    ? 'Enter number of BHK (e.g. 6)'
                    : 'Enter your property type (e.g. Godown, Clinic, Banquet Hall)',
                hintStyle: const TextStyle(fontSize: 12.5, color: AppColors.textHint),
                suffixText: flow.isHome ? 'BHK' : null,
                suffixStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppColors.textSecondary),
              ),
            ),
          ],
          if (flow.propertySelected) ...[
            const SizedBox(height: 22),
            const Pc99SectionTitle('Select Service'),
            const SizedBox(height: 4),
            const Text('Choose one or more services', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
            const SizedBox(height: 12),
            ...BookingFlowProvider.catalog.map((s) => _ServiceTile(
                  service: s,
                  flow: flow,
                  onToggle: () {
                    final selecting = !flow.selectedServiceIds.contains(s.id);
                    flow.toggleService(s.id);
                    // Reveal the More Options panel that expands below.
                    if (selecting) _nudgeScroll(170);
                  },
                )),
            const SizedBox(height: 8),
          ],
        ],
      ),
    );
  }
}

class _PreselectedServiceBanner extends StatelessWidget {
  const _PreselectedServiceBanner({required this.flow});

  final BookingFlowProvider flow;

  @override
  Widget build(BuildContext context) {
    final id = flow.selectedServiceIds.first;
    final service = flow.serviceById(id);
    if (service == null) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.25)),
      ),
      child: Row(
        children: [
          const Icon(Icons.check_circle, size: 20, color: AppColors.primary),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  service.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                const Text(
                  'Selected — choose property size below to continue',
                  style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
          TextButton(
            onPressed: () => flow.toggleService(id),
            child: const Text('Change'),
          ),
        ],
      ),
    );
  }
}

class _CategoryTabs extends StatelessWidget {
  const _CategoryTabs({required this.category, required this.onChanged});

  final String category;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    Widget tab(String id, String label, IconData icon) {
      final selected = category == id;
      return Expanded(
        child: InkWell(
          onTap: () => onChanged(id),
          borderRadius: BorderRadius.circular(10),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: selected ? AppColors.primary : Colors.transparent,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 18, color: selected ? Colors.white : AppColors.textSecondary),
                const SizedBox(width: 6),
                Text(
                  label,
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13.5,
                    color: selected ? Colors.white : AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          tab('home', 'Home', Icons.home_outlined),
          tab('commercial', 'Commercial', Icons.apartment_rounded),
        ],
      ),
    );
  }
}

class _ConfigChip extends StatelessWidget {
  const _ConfigChip({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 120),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.planSelectedBg : AppColors.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected ? AppColors.primary : AppColors.border,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
            color: selected ? AppColors.primary : AppColors.textPrimary,
          ),
        ),
      ),
    );
  }
}

class _ServiceTile extends StatelessWidget {
  const _ServiceTile({required this.service, required this.flow, required this.onToggle});

  final ServiceOption service;
  final BookingFlowProvider flow;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final selected = flow.selectedServiceIds.contains(service.id);
    final isAmc = flow.planIsAmc[service.id] ?? false;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Pc99Card(
        selected: selected,
        onTap: onToggle,
        child: Column(
          children: [
            Row(
              children: [
                Pc99IconBubble(icon: pc99ServiceIcon(service.icon)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(service.name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                      const SizedBox(height: 2),
                      Text(
                        flow.priceLabelForService(service.id, isAmc: isAmc),
                        style: const TextStyle(
                          color: AppColors.primary,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
                Pc99CheckBox(selected: selected),
              ],
            ),
            if (selected) ...[
              const Divider(height: 20, color: AppColors.divider),
              const Align(
                alignment: Alignment.centerLeft,
                child: Text('More Options', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
              ),
              const SizedBox(height: 8),
              ...() {
                final options = BookingFlowProvider.planOptionsFor(service.id);
                final widgets = <Widget>[];
                if (options.contains('one_time') || options.contains('2_service')) {
                  widgets.add(
                    _ModeRow(
                      title: options.contains('2_service') ? '2-Service Package' : 'One-Time Service',
                      subtitle: flow.priceLabelForService(service.id, isAmc: false),
                      selected: !isAmc,
                      onTap: () => flow.setPlan(service.id, isAmc: false),
                    ),
                  );
                }
                if (options.contains('amc')) {
                  if (widgets.isNotEmpty) widgets.add(const SizedBox(height: 8));
                  widgets.add(
                    _ModeRow(
                      title: 'AMC Package',
                      subtitle: flow.priceLabelForService(service.id, isAmc: true),
                      selected: isAmc,
                      onTap: () => flow.setPlan(service.id, isAmc: true),
                    ),
                  );
                }
                return widgets;
              }(),
            ],
          ],
        ),
      ),
    );
  }
}

class _ModeRow extends StatelessWidget {
  const _ModeRow({
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.planSelectedBg : AppColors.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: selected ? AppColors.primary : AppColors.border, width: selected ? 1.5 : 1),
        ),
        child: Row(
          children: [
            Pc99Radio(selected: selected),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                  const SizedBox(height: 2),
                  Text(subtitle, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class DateTimeSelectionScreen extends StatelessWidget {
  const DateTimeSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final month = DateTime(flow.selectedDate.year, flow.selectedDate.month);
    final daysInMonth = DateUtils.getDaysInMonth(month.year, month.month);
    final firstWeekday = DateTime(month.year, month.month, 1).weekday % 7; // Sun=0

    return Pc99Scaffold(
      title: 'Select Date & Time',
      onBack: () => context.pop(),
      floatingBottom: Pc99PrimaryButton(
        label: 'Continue',
        onPressed: flow.selectedSlot == null ? null : () => context.push('/book/summary'),
      ),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        children: [
          Row(
            children: [
              IconButton(
                onPressed: () => flow.setDate(DateTime(month.year, month.month - 1, 1)),
                icon: const Icon(Icons.chevron_left_rounded, size: 22),
                visualDensity: VisualDensity.compact,
              ),
              Expanded(
                child: Text(
                  DateFormat('MMMM yyyy').format(month),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15),
                ),
              ),
              IconButton(
                onPressed: () => flow.setDate(DateTime(month.year, month.month + 1, 1)),
                icon: const Icon(Icons.chevron_right_rounded, size: 22),
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                .map((d) => Expanded(
                      child: Center(
                        child: Text(d, style: const TextStyle(color: AppColors.textMuted, fontSize: 10.5, fontWeight: FontWeight.w600)),
                      ),
                    ))
                .toList(),
          ),
          const SizedBox(height: 6),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: firstWeekday + daysInMonth,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 7,
              mainAxisSpacing: 4,
              crossAxisSpacing: 4,
              childAspectRatio: 1.35,
            ),
            itemBuilder: (context, index) {
              if (index < firstWeekday) return const SizedBox.shrink();
              final day = index - firstWeekday + 1;
              final date = DateTime(month.year, month.month, day);
              final today = DateTime.now();
              final minDate = DateTime(today.year, today.month, today.day);
              final selected = DateUtils.isSameDay(date, flow.selectedDate);
              final disabled = date.isBefore(minDate);
              return InkWell(
                onTap: disabled ? null : () => flow.setDate(date),
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: selected ? AppColors.primary : Colors.transparent,
                    shape: BoxShape.circle,
                  ),
                  child: Text(
                    '$day',
                    style: TextStyle(
                      fontSize: 12.5,
                      color: disabled
                          ? AppColors.textMuted.withValues(alpha: 0.35)
                          : (selected ? Colors.white : AppColors.textPrimary),
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 18),
          const Text('Select exact service time', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 4),
          const Text('Choose a preferred start time · 10 AM to 7:30 PM', style: TextStyle(color: AppColors.textMuted, fontSize: 11.5)),
          const SizedBox(height: 10),
          GridView.count(
            crossAxisCount: 3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
            childAspectRatio: 2.4,
            children: BookingFlowProvider.timeSlots.map((slot) {
              final selected = flow.selectedSlot == slot;
              return InkWell(
                onTap: () => flow.setSlot(slot),
                borderRadius: BorderRadius.circular(10),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 120),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: selected ? AppColors.planSelectedBg : AppColors.surface,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: selected ? AppColors.primary : AppColors.border,
                      width: selected ? 1.5 : 1,
                    ),
                  ),
                  child: Text(
                    slot,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                      color: selected ? AppColors.primary : AppColors.textPrimary,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

class BookingSummaryScreen extends StatefulWidget {
  const BookingSummaryScreen({super.key});

  @override
  State<BookingSummaryScreen> createState() => _BookingSummaryScreenState();
}

class _BookingSummaryScreenState extends State<BookingSummaryScreen> {
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _ensureCatalog());
  }

  Future<void> _ensureCatalog() async {
    final flow = context.read<BookingFlowProvider>();
    if (flow.rates.isNotEmpty || flow.ratesLoading) return;
    flow.setRatesLoading(true);
    try {
      final rates = await CatalogService(context.read<ApiClient>()).list();
      if (!mounted) return;
      flow.setRates(rates);
    } catch (e) {
      if (!mounted) return;
      flow.setRatesError('$e');
    }
  }

  Future<void> _confirm() async {
    final auth = context.read<AuthProvider>();
    if (!auth.loggedIn) {
      auth.setPendingRoute('/book/summary');
      context.push('/login');
      return;
    }

    final flow = context.read<BookingFlowProvider>();
    if (flow.selectedServices.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select at least one service first'), backgroundColor: AppColors.danger),
      );
      return;
    }
    if (!flow.hasServiceAddress) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter your full service address'), backgroundColor: AppColors.danger),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final api = context.read<ApiClient>();
      if (flow.rates.isEmpty) {
        final catalog = await CatalogService(api).list();
        flow.setRates(catalog);
      }
      final first = flow.selectedServices.first;
      final isAmc = flow.planIsAmc[first.id] ?? false;
      // Any selected service without a CRM fixed rate → Price Confirmation Pending.
      var pricePending = false;
      final missing = <String>[];
      for (final s in flow.selectedServices) {
        final amt = flow.amountForService(s.id);
        if (amt == null || amt <= 0) {
          pricePending = true;
          missing.add(s.name);
        }
      }
      final rate = flow.matchRate();
      if (rate == null) pricePending = true;
      final amount = flow.amountForService(first.id);
      final rateId = pricePending ? 0 : (rate?.id ?? 0);
      final parts = _slotParts(flow.selectedSlot);
      final pendingNote = missing.isEmpty
          ? 'Price Confirmation Pending'
          : 'Price Confirmation Pending (${missing.join(', ')})';
      final booking = await BookingService(api).book(
        serviceType: flow.selectedServices.map((s) => s.name).join(', '),
        pricingRateId: rateId,
        packageTier: 'standard',
        address: flow.serviceAddress.trim(),
        city: flow.serviceCity.trim(),
        area: flow.serviceArea.trim(),
        bhkSize: flow.bhkSizeForApi,
        propertyType: flow.propertyTypeForApi,
        bookingType: isAmc ? 'amc' : 'one_time',
        priceConfirmationPending: pricePending,
        notes:
            'App booking · ${flow.propertyLabel} · ${flow.propertyConfig} · ${flow.selectedSlot}'
            '${pricePending ? ' · $pendingNote' : ' · CRM ₹${(amount ?? 0).round()}'}',
        scheduleDatetime: DateTime(
          flow.selectedDate.year,
          flow.selectedDate.month,
          flow.selectedDate.day,
          parts.$1,
          parts.$2,
        ).toUtc().toIso8601String(),
        timeSlot: flow.selectedSlot,
      );
      flow.setConfirmed(booking);
      if (!mounted) return;
      context.go('/book/confirmed');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not confirm booking: $e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Returns (hour, minute) in 24h for a label like "10:30 AM".
  (int, int) _slotParts(String? slot) {
    if (slot == null || slot.isEmpty) return (10, 0);
    final match = RegExp(r'(\d{1,2}):(\d{2})\s*(AM|PM)', caseSensitive: false).firstMatch(slot);
    if (match == null) return (10, 0);
    var hour = int.tryParse(match.group(1)!) ?? 10;
    final minute = int.tryParse(match.group(2)!) ?? 0;
    final meridiem = (match.group(3) ?? 'AM').toUpperCase();
    if (meridiem == 'PM' && hour < 12) hour += 12;
    if (meridiem == 'AM' && hour == 12) hour = 0;
    return (hour, minute);
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final total = flow.estimatedTotal;
    final allPriced = flow.selectedServices.isNotEmpty &&
        flow.selectedServices.every((s) {
          final amount = flow.amountForService(s.id);
          return amount != null && amount > 0;
        });
    final hasPriced = allPriced && total > 0;
    final loggedIn = context.watch<AuthProvider>().loggedIn;

    return Pc99Scaffold(
      title: 'Booking Summary',
      onBack: () => context.pop(),
      floatingBottom: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: hasPriced ? AppColors.successSoft : const Color(0xFFFFF7ED),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                Icon(
                  hasPriced ? Icons.currency_rupee_rounded : Icons.schedule_outlined,
                  color: hasPriced ? AppColors.primary : AppColors.warning,
                  size: 18,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    hasPriced
                        ? 'Total ${BookingFlowProvider.formatInr(total)} · Unpaid until payment received'
                        : 'Fixed rate not found · booking will be created as Price Confirmation Pending',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
                  ),
                ),
              ],
            ),
          ),
          Pc99PrimaryButton(
            label: _busy
                ? 'Confirming…'
                : (loggedIn
                    ? (hasPriced ? 'Confirm Booking' : 'Request Price Confirmation')
                    : 'Login to Confirm'),
            onPressed: _confirm,
            busy: _busy,
          ),
        ],
      ),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        children: [
          Pc99Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Pc99SectionTitle('Property', action: 'Change', onAction: () => context.go('/book/property')),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Pc99IconBubble(icon: flow.isHome ? Icons.home_outlined : Icons.apartment_rounded),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(flow.propertyLabel, style: const TextStyle(fontWeight: FontWeight.w800)),
                          if ((flow.propertyConfig ?? '').isNotEmpty) ...[
                            const SizedBox(height: 3),
                            Text(flow.propertyConfig!, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Pc99Card(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Service Address',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  initialValue: flow.serviceAddress,
                  onChanged: (v) => flow.setServiceAddress(address: v),
                  maxLines: 1,
                  style: const TextStyle(fontSize: 13),
                  decoration: const InputDecoration(
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                    hintText: 'Flat / building, street, landmark',
                    hintStyle: TextStyle(fontSize: 12, color: AppColors.textHint),
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        initialValue: flow.serviceArea,
                        onChanged: (v) => flow.setServiceAddress(area: v),
                        style: const TextStyle(fontSize: 13),
                        decoration: const InputDecoration(
                          isDense: true,
                          contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                          hintText: 'Area',
                          hintStyle: TextStyle(fontSize: 12, color: AppColors.textHint),
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: TextFormField(
                        initialValue: flow.serviceCity,
                        onChanged: (v) => flow.setServiceAddress(city: v),
                        style: const TextStyle(fontSize: 13),
                        decoration: const InputDecoration(
                          isDense: true,
                          contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                          hintText: 'City',
                          hintStyle: TextStyle(fontSize: 12, color: AppColors.textHint),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Pc99Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Pc99SectionTitle('Selected Services'),
                const SizedBox(height: 8),
                if (flow.selectedServices.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Text('No services selected yet', style: TextStyle(color: AppColors.textMuted)),
                  )
                else
                  ...flow.selectedServices.map((s) {
                    return Column(
                      children: [
                        const Divider(color: AppColors.divider),
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              Icon(pc99ServiceIcon(s.icon), color: AppColors.textSecondary, size: 22),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(s.name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                                    const SizedBox(height: 2),
                                    Text(flow.planLabel(s.id), style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
                                  ],
                                ),
                              ),
                              Text(
                                flow.priceLabelForService(s.id),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 13,
                                  color: AppColors.primary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    );
                  }),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Pc99Card(
            child: Row(
              children: [
                const Icon(Icons.calendar_month_outlined, color: AppColors.primary),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    '${DateFormat('EEE, d MMM yyyy').format(flow.selectedDate)} · ${flow.selectedSlot}',
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
          if (hasPriced) ...[
            const SizedBox(height: 12),
            Pc99Card(
              child: Column(
                children: [
                  Row(
                    children: [
                      const Expanded(child: Text('Subtotal', style: TextStyle(color: AppColors.textMuted, fontSize: 13))),
                      Text(BookingFlowProvider.formatInr(total), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  const Divider(color: AppColors.divider),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Expanded(
                        child: Text('Total Amount', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                      ),
                      Text(
                        BookingFlowProvider.formatInr(total),
                        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.successSoft,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.primary.withValues(alpha: 0.35)),
            ),
            child: Row(
              children: [
                Icon(
                  hasPriced ? Icons.currency_rupee_rounded : Icons.info_outline_rounded,
                  color: AppColors.primary,
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    hasPriced
                        ? 'Price from CRM rate card. Pay after service.'
                        : 'Select property size + service, then Continue twice to open this summary with CRM prices.',
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class BookingConfirmedScreen extends StatelessWidget {
  const BookingConfirmedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final booking = flow.confirmedBooking;
    final id = booking?.code ?? 'BK-${DateFormat('yyMMdd').format(DateTime.now())}${booking?.id ?? 1578}';

    return Pc99Scaffold(
      showClose: true,
      onBack: () => context.go('/home'),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
        children: [
          const SizedBox(height: 12),
          Center(
            child: Container(
              width: 84,
              height: 84,
              decoration: const BoxDecoration(color: AppColors.primary, shape: BoxShape.circle),
              child: const Icon(Icons.check_rounded, color: Colors.white, size: 46),
            ),
          ),
          const SizedBox(height: 18),
          const Text(
            'Your booking is confirmed!',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            flow.isHome
                ? 'Our team will contact you to confirm the service'
                : 'Final price will be shared after inspection',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13, color: AppColors.textMuted),
          ),
          const SizedBox(height: 18),
          Pc99Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Booking ID', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Expanded(child: Text(id, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18))),
                    IconButton(
                      onPressed: () => pc99Copy(context, id, label: 'Booking ID copied'),
                      icon: const Icon(Icons.copy_rounded, color: AppColors.textSecondary),
                    ),
                  ],
                ),
                const Divider(color: AppColors.divider),
                const Text('We have sent the details to your', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                const SizedBox(height: 4),
                Text(
                  '+91 ${context.watch<AuthProvider>().profile?.mobile ?? '—'}',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const Pc99SectionTitle('Booking Status'),
          const SizedBox(height: 12),
          ...[
            ('Confirmed', true),
            ('Technician Assigned', false),
            ('On The Way', false),
            ('Service Completed', false),
          ].asMap().entries.map((e) {
            final done = e.key == 0;
            return Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Row(
                children: [
                  Column(
                    children: [
                      Icon(done ? Icons.check_circle : Icons.radio_button_unchecked, color: done ? AppColors.primary : AppColors.border),
                      if (e.key < 3) Container(width: 2, height: 18, color: AppColors.border),
                    ],
                  ),
                  const SizedBox(width: 10),
                  Text(e.value.$1, style: TextStyle(fontWeight: FontWeight.w700, color: done ? AppColors.textPrimary : AppColors.textMuted)),
                ],
              ),
            );
          }),
          const SizedBox(height: 10),
          Pc99PrimaryButton(label: 'Back to Home', onPressed: () => context.go('/home')),
        ],
      ),
    );
  }
}
