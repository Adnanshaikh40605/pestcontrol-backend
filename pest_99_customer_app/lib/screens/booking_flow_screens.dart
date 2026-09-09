import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/booking_timezone.dart';
import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';
import '../providers/booking_flow_provider.dart';
import '../services/customer_services.dart';
import '../shared/widgets/pc99_widgets.dart';
import '../widgets/service_address_section.dart';
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
    flow.beginWithService(id);
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
    final locked = flow.lockedService;

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
          Text(
            locked != null
                ? 'Complete your ${locked.name} booking'
                : 'Select your property type to get started',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
          if (locked != null) ...[
            const SizedBox(height: 14),
            _LockedServiceHeader(
              service: locked,
              onChange: flow.unlockServiceSelection,
            ),
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
            Pc99SectionTitle(locked != null ? '${locked.name} Services' : 'Select Service'),
            const SizedBox(height: 4),
            Text(
              locked != null ? 'Choose your service plan' : 'Choose one or more services',
              style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
            ),
            const SizedBox(height: 12),
            ...flow.visibleCatalog.map((s) => _ServiceTile(
                  service: s,
                  flow: flow,
                  allowToggle: locked == null,
                  onToggle: () {
                    final selecting = !flow.selectedServiceIds.contains(s.id);
                    flow.toggleService(s.id);
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

class _LockedServiceHeader extends StatelessWidget {
  const _LockedServiceHeader({required this.service, required this.onChange});

  final ServiceOption service;
  final VoidCallback onChange;

  @override
  Widget build(BuildContext context) {
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
          Pc99IconBubble(icon: pc99ServiceIcon(service.icon)),
          const SizedBox(width: 12),
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
                  'Selected from Home — choose property size below',
                  style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
          TextButton(onPressed: onChange, child: const Text('Change')),
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
  const _ServiceTile({
    required this.service,
    required this.flow,
    required this.onToggle,
    this.allowToggle = true,
  });

  final ServiceOption service;
  final BookingFlowProvider flow;
  final VoidCallback onToggle;
  final bool allowToggle;

  @override
  Widget build(BuildContext context) {
    final selected = flow.selectedServiceIds.contains(service.id);
    final isAmc = flow.planIsAmc[service.id] ?? false;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Pc99Card(
        selected: selected,
        onTap: allowToggle ? onToggle : null,
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
                if (allowToggle) Pc99CheckBox(selected: selected),
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

  Future<void> _openClockPicker(BuildContext context, BookingFlowProvider flow) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: flow.selectedHour, minute: flow.selectedMinute),
      initialEntryMode: TimePickerEntryMode.dial,
      helpText: 'SELECT TIME',
      confirmText: 'SET TIME',
      cancelText: 'CANCEL',
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: false),
          child: Theme(
            data: Theme.of(context).copyWith(
              timePickerTheme: TimePickerThemeData(
                backgroundColor: Colors.white,
                dialHandColor: AppColors.primary,
                dialBackgroundColor: AppColors.planSelectedBg,
                hourMinuteColor: WidgetStateColor.resolveWith((states) {
                  if (states.contains(WidgetState.selected)) {
                    return AppColors.primary;
                  }
                  return AppColors.planSelectedBg;
                }),
                hourMinuteTextColor: WidgetStateColor.resolveWith((states) {
                  if (states.contains(WidgetState.selected)) {
                    return Colors.white;
                  }
                  return AppColors.textPrimary;
                }),
                dayPeriodColor: AppColors.primary,
                dayPeriodTextColor: WidgetStateColor.resolveWith((states) {
                  if (states.contains(WidgetState.selected)) {
                    return Colors.white;
                  }
                  return AppColors.textPrimary;
                }),
              ),
              colorScheme: Theme.of(context).colorScheme.copyWith(
                    primary: AppColors.primary,
                    onPrimary: Colors.white,
                    surface: Colors.white,
                    onSurface: AppColors.textPrimary,
                  ),
            ),
            child: child!,
          ),
        );
      },
    );
    if (picked == null || !context.mounted) return;

    if (!BookingTimezone.isWithinServiceWindow(picked.hour, picked.minute)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please choose a time between 10:00 AM and 7:30 PM'),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }
    if (!BookingTimezone.isNotInPast(flow.selectedDate, picked.hour, picked.minute)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('That time has already passed today. Choose a later time.'),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }
    flow.setTime(picked.hour, picked.minute);
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final month = DateTime(flow.selectedDate.year, flow.selectedDate.month);
    final daysInMonth = DateUtils.getDaysInMonth(month.year, month.month);
    final firstWeekday = DateTime(month.year, month.month, 1).weekday % 7; // Sun=0
    final minDate = BookingTimezone.today();
    final canContinue = flow.hasValidSelectedTime;

    return Pc99Scaffold(
      title: 'Select Date & Time',
      onBack: () => context.pop(),
      floatingBottom: Pc99PrimaryButton(
        label: 'Continue',
        onPressed: canContinue ? () => context.push('/book/summary') : null,
      ),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        children: [
          Row(
            children: [
              IconButton(
                onPressed: () {
                  final prev = DateTime(month.year, month.month - 1, 1);
                  final keepDay = flow.selectedDate.day.clamp(1, DateUtils.getDaysInMonth(prev.year, prev.month));
                  final candidate = DateTime(prev.year, prev.month, keepDay);
                  flow.setDate(candidate.isBefore(minDate) ? minDate : candidate);
                },
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
                onPressed: () {
                  final next = DateTime(month.year, month.month + 1, 1);
                  final keepDay = flow.selectedDate.day.clamp(1, DateUtils.getDaysInMonth(next.year, next.month));
                  flow.setDate(DateTime(next.year, next.month, keepDay));
                },
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
          const Text('Select Time', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 4),
          const Text(
            'Tap to open the clock · 10:00 AM to 7:30 PM (Asia/Kolkata)',
            style: TextStyle(color: AppColors.textMuted, fontSize: 11.5),
          ),
          const SizedBox(height: 12),
          Material(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            child: InkWell(
              onTap: () => _openClockPicker(context, flow),
              borderRadius: BorderRadius.circular(16),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: canContinue ? AppColors.primary : AppColors.border,
                    width: canContinue ? 1.5 : 1,
                  ),
                  color: canContinue ? AppColors.planSelectedBg.withValues(alpha: 0.45) : Colors.white,
                ),
                child: Column(
                  children: [
                    Icon(Icons.schedule_rounded, color: AppColors.primary, size: 36),
                    const SizedBox(height: 10),
                    Text(
                      flow.selectedSlot,
                      style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                        color: AppColors.primary,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      DateFormat('EEEE, d MMMM yyyy').format(flow.selectedDate),
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12.5, color: AppColors.textMuted, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 14),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Text(
                        'SET TIME',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12, letterSpacing: 0.4),
                      ),
                    ),
                    if (!canContinue) ...[
                      const SizedBox(height: 10),
                      const Text(
                        'Choose a valid future time within the service window',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 11.5, color: AppColors.danger, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ],
                ),
              ),
            ),
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
        const SnackBar(
          content: Text('Enter your service address and select city & area'),
          backgroundColor: AppColors.danger,
        ),
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
      final pendingNote = missing.isEmpty
          ? 'Price Confirmation Pending'
          : 'Price Confirmation Pending (${missing.join(', ')})';
      final scheduleIso = BookingTimezone.toIstIso8601(
        flow.selectedDate,
        flow.selectedHour,
        flow.selectedMinute,
      );
      final booking = await BookingService(api).book(
        serviceType: flow.selectedServices.map((s) => s.name).join(', '),
        pricingRateId: rateId,
        packageTier: 'standard',
        address: flow.serviceAddress.trim(),
        fullAddress: flow.serviceFullAddress.trim(),
        city: flow.serviceCity.trim(),
        area: flow.serviceArea.trim(),
        masterCityId: flow.masterCityId,
        masterLocationId: flow.masterLocationId,
        latitude: flow.serviceLatitude,
        longitude: flow.serviceLongitude,
        placeId: flow.servicePlaceId.trim().isEmpty ? null : flow.servicePlaceId.trim(),
        bhkSize: flow.bhkSizeForApi,
        propertyType: flow.propertyTypeForApi,
        bookingType: isAmc ? 'amc' : 'one_time',
        priceConfirmationPending: pricePending,
        notes:
            'App booking · ${flow.propertyLabel} · ${flow.propertyConfig} · ${flow.selectedSlot}'
            '${pricePending ? ' · $pendingNote' : ' · CRM ₹${(amount ?? 0).round()}'}',
        scheduleDatetime: scheduleIso,
        timeSlot: flow.selectedSlot,
        bookingDate: BookingTimezone.bookingDate(flow.selectedDate),
        bookingTime: BookingTimezone.bookingTime24(flow.selectedHour, flow.selectedMinute),
        timezone: BookingTimezone.id,
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
      floatingBottom: Pc99PrimaryButton(
        label: _busy
            ? 'Confirming…'
            : (loggedIn
                ? (hasPriced ? 'Confirm Booking' : 'Request Price Confirmation')
                : 'Login to Confirm'),
        onPressed: _confirm,
        busy: _busy,
      ),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        children: [
          Pc99Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Pc99SectionTitle(
                  'Property',
                  action: 'Change',
                  onAction: () {
                    final lock = flow.lockedServiceId;
                    context.go(
                      lock != null ? '/book/property?service=$lock' : '/book/property',
                    );
                  },
                ),
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
                const ServiceAddressSection(),
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
