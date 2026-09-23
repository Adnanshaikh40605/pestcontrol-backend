import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/api_config.dart';
import '../core/api_client.dart';
import '../core/booking_timezone.dart';
import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';
import '../providers/booking_flow_provider.dart';
import '../services/customer_services.dart';
import '../shared/widgets/pc99_widgets.dart';
import '../shared/widgets/service_guidelines_card.dart';
import '../utils/catalog_pricing.dart';
import '../widgets/booking_address_field.dart';

/// Website-matched single-screen booking form (Confirm Your Booking).
class WebsiteBookingScreen extends StatefulWidget {
  const WebsiteBookingScreen({
    super.key,
    this.initialServiceId,
    this.embeddedInShell = false,
  });

  final String? initialServiceId;

  /// When true (Home tab), hide the back button — bottom nav is the exit.
  final bool embeddedInShell;

  @override
  State<WebsiteBookingScreen> createState() => _WebsiteBookingScreenState();
}

class _WebsiteBookingScreenState extends State<WebsiteBookingScreen> {
  static const _green = Color(0xFF087B3D);
  static const _navy = Color(0xFF092456);
  static const _line = Color(0xFFDBE8DF);
  static const _soft = Color(0xFFEFFAF3);

  final _nameCtrl = TextEditingController();
  final _mobileCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();

  Map<String, String> _errors = {};
  String? _submitMessage;
  bool _busy = false;
  bool _otpOpen = false;
  bool _otpSending = false;
  bool _otpVerifying = false;
  String _otpError = '';
  String _otpHint = '';
  String _otpMobile = '';
  int _resendCooldown = 0;
  BookingFlowProvider? _draft;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadCatalog();
      _applyInitial();
      _prefillProfile();
    });
  }

  void _applyInitial() {
    final id = widget.initialServiceId?.trim();
    if (id == null || id.isEmpty) return;
    context.read<BookingFlowProvider>().beginWithService(id);
  }

  void _prefillProfile() {
    final auth = context.read<AuthProvider>();
    final flow = context.read<BookingFlowProvider>();
    final profile = auth.profile;
    if (profile == null) return;
    if (flow.fullName.isEmpty && profile.fullName.trim().isNotEmpty) {
      flow.setFullName(profile.fullName.trim());
      _nameCtrl.text = flow.fullName;
    }
    if (flow.mobile.isEmpty && profile.mobile.replaceAll(RegExp(r'\D'), '').length == 10) {
      flow.setMobile(profile.mobile);
      _mobileCtrl.text = flow.mobile;
    }
  }

  Future<void> _loadCatalog() async {
    final flow = context.read<BookingFlowProvider>();
    flow.setRatesLoading(true);
    try {
      final rates = await CatalogService(context.read<ApiClient>())
          .list()
          .timeout(const Duration(seconds: 8));
      if (!mounted) return;
      flow.setRates(rates);
    } catch (e) {
      if (!mounted) return;
      flow.setRatesError('$e');
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _addressCtrl.dispose();
    _otpCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final flow = context.read<BookingFlowProvider>();
    final initial = flow.preferredDate.isNotEmpty
        ? DateTime.tryParse(flow.preferredDate) ?? BookingTimezone.today()
        : BookingTimezone.today();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial.isBefore(BookingTimezone.today()) ? BookingTimezone.today() : initial,
      firstDate: BookingTimezone.today(),
      lastDate: BookingTimezone.today().add(const Duration(days: 90)),
      builder: (context, child) => Theme(
        data: Theme.of(context).copyWith(
          colorScheme: Theme.of(context).colorScheme.copyWith(primary: _green),
        ),
        child: child!,
      ),
    );
    if (picked != null) flow.setPreferredDate(picked);
  }

  Future<void> _pickTime() async {
    final flow = context.read<BookingFlowProvider>();
    final parts = flow.preferredTimeParts ?? (10, 0);
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: parts.$1, minute: parts.$2),
      builder: (context, child) => Theme(
        data: Theme.of(context).copyWith(
          colorScheme: Theme.of(context).colorScheme.copyWith(primary: _green),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      // Snap to 5-minute steps like website ClockTimePicker.
      final snapped = ((picked.minute / 5).round() * 5).clamp(0, 55);
      flow.setPreferredTime(picked.hour, snapped);
    }
  }

  Future<void> _openOtherPremiseHelp() async {
    final wa = Uri.parse(
      'https://wa.me/${BookingFlowProvider.supportWhatsApp}'
      '?text=${Uri.encodeComponent(BookingFlowProvider.otherPremiseWhatsAppMessage)}',
    );
    final tel = Uri.parse('tel:${BookingFlowProvider.supportPhoneTel}');
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Need a custom quote?',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: _navy),
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(ctx),
                  icon: const Icon(Icons.close),
                  tooltip: 'Close',
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'For premise sizes outside our standard 1 RK–6 BHK list, talk to an agent for pricing. '
              'Online booking stays on hold until you get a quote.',
              style: TextStyle(fontSize: 13, color: AppColors.textMuted, height: 1.35),
            ),
            const SizedBox(height: 16),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFF25D366)),
              onPressed: () => launchUrl(wa, mode: LaunchMode.externalApplication),
              child: const Text('WhatsApp'),
            ),
            const SizedBox(height: 8),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: _navy),
              onPressed: () => launchUrl(tel),
              child: const Text('Call +91 80807 48282'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Keep browsing'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showTreatmentInfo(String quality) async {
    final detail = BookingFlowProvider.treatmentDetails[quality];
    if (detail == null) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                detail.title,
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: _navy),
              ),
              const SizedBox(height: 12),
              ...detail.bullets.map(
                (b) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('•  ', style: TextStyle(fontWeight: FontWeight.w800, color: _green)),
                      Expanded(child: Text(b, style: const TextStyle(fontSize: 13, height: 1.35))),
                    ],
                  ),
                ),
              ),
              if (detail.whyTitle != null) ...[
                const SizedBox(height: 8),
                Text(detail.whyTitle!, style: const TextStyle(fontWeight: FontWeight.w800, color: _navy)),
                const SizedBox(height: 4),
                Text(detail.whyBody ?? '', style: const TextStyle(fontSize: 13, height: 1.35)),
              ],
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  style: FilledButton.styleFrom(backgroundColor: _green),
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Got it'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _onConfirm() async {
    final flow = context.read<BookingFlowProvider>();
    if (flow.isOtherPremiseSize) {
      setState(() {
        _errors = {
          ..._errors,
          'premiseSize': 'Please call or WhatsApp us for a custom quote',
        };
        _submitMessage = null;
      });
      await _openOtherPremiseHelp();
      return;
    }

    final errors = flow.validate();
    setState(() {
      _errors = errors;
      _submitMessage = null;
    });
    if (errors.isNotEmpty) {
      setState(() => _submitMessage = errors.values.first);
      return;
    }

    setState(() {
      _busy = true;
      _otpSending = true;
    });
    try {
      final auth = AuthService(context.read<ApiClient>());
      final res = await auth.sendOtp(
        mobile: flow.mobile,
        purpose: 'website_booking',
        fullName: flow.fullName.trim(),
      );
      if (!mounted) return;
      _draft = flow;
      setState(() {
        _otpOpen = true;
        _otpMobile = '${res['mobile'] ?? flow.mobile}';
        _otpCtrl.clear();
        _otpError = '';
        _otpHint = res['dev_otp'] != null ? 'Local DEBUG OTP: ${res['dev_otp']}' : '';
        _resendCooldown = (res['resend_after'] is num) ? (res['resend_after'] as num).toInt() : 2;
      });
      _tickResend();
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitMessage = '$e');
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _otpSending = false;
        });
      }
    }
  }

  void _tickResend() {
    if (_resendCooldown <= 0) return;
    Future.delayed(const Duration(seconds: 1), () {
      if (!mounted || !_otpOpen) return;
      setState(() => _resendCooldown = (_resendCooldown - 1).clamp(0, 999));
      if (_resendCooldown > 0) _tickResend();
    });
  }

  Future<void> _resendOtp() async {
    final flow = _draft ?? context.read<BookingFlowProvider>();
    if (_resendCooldown > 0 || _otpSending || _otpVerifying) return;
    setState(() {
      _otpSending = true;
      _otpError = '';
    });
    try {
      final auth = AuthService(context.read<ApiClient>());
      final res = await auth.sendOtp(
        mobile: flow.mobile,
        purpose: 'website_booking',
        fullName: flow.fullName.trim(),
      );
      if (!mounted) return;
      setState(() {
        _otpMobile = '${res['mobile'] ?? flow.mobile}';
        _otpHint = res['dev_otp'] != null ? 'Local DEBUG OTP: ${res['dev_otp']}' : '';
        _resendCooldown = (res['resend_after'] is num) ? (res['resend_after'] as num).toInt() : 2;
      });
      _tickResend();
    } catch (e) {
      if (!mounted) return;
      setState(() => _otpError = '$e');
    } finally {
      if (mounted) setState(() => _otpSending = false);
    }
  }

  Future<void> _verifyAndCreate() async {
    final flow = _draft ?? context.read<BookingFlowProvider>();
    final otp = _otpCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (otp.length != 4) {
      setState(() => _otpError = 'Enter the 4-digit OTP');
      return;
    }
    setState(() {
      _otpVerifying = true;
      _otpError = '';
    });
    try {
      final api = context.read<ApiClient>();
      final verifyData = await api.post(
        ApiConfig.otpVerify,
        auth: false,
        body: {
          'mobile': _otpMobile.isNotEmpty ? _otpMobile : flow.mobile,
          'otp': otp,
          'purpose': 'website_booking',
        },
      );
      final token = '${verifyData['otp_verification_token'] ?? ''}';
      if (token.isEmpty) {
        setState(() => _otpError = 'Verification succeeded but no booking token was issued.');
        return;
      }

      final q = flow.quote;
      final quality = flow.isInspectionQuote
          ? 'standard'
          : (flow.showTreatmentQuality
              ? (flow.treatmentQuality.isEmpty ? 'standard' : flow.treatmentQuality)
              : 'standard');
      final qualityLabel = flow.showTreatmentQuality
          ? (quality == 'premium' ? 'Premium' : 'Standard')
          : 'Standard';
      final planLabel = flow.bookingTypeForApi == 'amc'
          ? 'AMC · 3 visits'
          : (flow.isBedBugsPrimaryPlan ? BookingFlowProvider.bedBugPlanTitle : 'One-Time');
      final priceNote = q.pricePending
          ? 'Inspection / on-request pricing'
          : 'CRM ₹${q.offerPrice.round()} excl. GST';
      final booking = await BookingService(api).createWebsiteBooking(
        fullName: flow.fullName.trim(),
        mobile: (_otpMobile.isNotEmpty ? _otpMobile : flow.mobile).replaceAll(RegExp(r'\D'), ''),
        serviceType: q.serviceTypeLabel,
        packageTier: q.packageTier,
        propertyType: flow.propertyTypeForApi,
        bhkSize: flow.bhkSizeForApi,
        address: flow.streetAddress.trim(),
        fullAddress: flow.serviceFullAddress.isNotEmpty
            ? flow.serviceFullAddress
            : flow.streetAddress.trim(),
        area: flow.serviceArea,
        city: flow.serviceCity.trim().isNotEmpty
            ? flow.serviceCity.trim()
            : _guessCity(flow.streetAddress),
        bookingType: flow.bookingTypeForApi,
        otpVerificationToken: token,
        pricingRateId: q.pricingRateId,
        priceConfirmationPending: q.pricePending,
        bookingDate: flow.preferredDate,
        bookingTime: flow.bookingTime24,
        timezone: BookingTimezone.id,
        timeSlot: flow.timeSlotLabel,
        latitude: flow.serviceLatitude,
        longitude: flow.serviceLongitude,
        notes:
            'App booking · ${flow.isCommercial ? 'Commercial' : 'Home (Residential)'} · '
            '${flow.bhkSizeForApi.isEmpty ? '—' : flow.bhkSizeForApi} · $qualityLabel · $planLabel · '
            '${flow.timeSlotLabel} · $priceNote · Lead: Customer App',
      );
      flow.setConfirmed(booking, mobileOverride: flow.mobile);
      if (!mounted) return;
      setState(() => _otpOpen = false);
      context.go('/book/confirmed');
    } catch (e) {
      if (!mounted) return;
      setState(() => _otpError = '$e');
    } finally {
      if (mounted) setState(() => _otpVerifying = false);
    }
  }

  String _guessCity(String address) {
    final lower = address.toLowerCase();
    if (lower.contains('mumbai') || lower.contains('thane') || lower.contains('navi mumbai')) {
      return 'Mumbai';
    }
    if (lower.contains('pune') || lower.contains('pimpri') || lower.contains('chinchwad')) {
      return 'Pune';
    }
    if (lower.contains('lonavala') || lower.contains('khandala')) return 'Lonavala';
    return 'Pune';
  }

  /// Density tokens matched to pestcontrol99.com home booking CSS.
  /// Uses available body height (below header, above bottom nav) — not full screen height.
  _FormDensity _densityFor(double bodyHeight) {
    // Shell nav (~56–68) already shrinks body vs website; stay dense by default.
    if (bodyHeight < 620) {
      return const _FormDensity(
        gap: 4,
        colGap: 5,
        fieldH: 32,
        choiceH: 32,
        propH: 24,
        priceH: 30,
        ctaH: 36,
        headerH: 42,
        formPadH: 8,
        formPadV: 4,
        titleSize: 14,
        warrantySize: 9,
        labelSize: 8.5,
        fieldFont: 11,
        choiceTitle: 10.5,
        choiceSub: 7.5,
        ctaFont: 13,
        showTrust: false,
        heroPadV: 5,
        heroTitle: 16,
      );
    }
    if (bodyHeight < 700) {
      return const _FormDensity(
        gap: 5,
        colGap: 6,
        fieldH: 34,
        choiceH: 36,
        propH: 26,
        priceH: 34,
        ctaH: 40,
        headerH: 44,
        formPadH: 10,
        formPadV: 6,
        titleSize: 14,
        warrantySize: 9.5,
        labelSize: 8.5,
        fieldFont: 11.5,
        choiceTitle: 11,
        choiceSub: 8,
        ctaFont: 14,
        showTrust: false,
        heroPadV: 6,
        heroTitle: 17,
      );
    }
    return const _FormDensity(
      gap: 6,
      colGap: 7,
      fieldH: 36,
      choiceH: 38,
      propH: 28,
      priceH: 36,
      ctaH: 42,
      headerH: 46,
      formPadH: 10,
      formPadV: 8,
      titleSize: 15,
      warrantySize: 10,
      labelSize: 9,
      fieldFont: 12,
      choiceTitle: 11,
      choiceSub: 8,
      ctaFont: 14.5,
      showTrust: true,
      heroPadV: 8,
      heroTitle: 18,
    );
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final q = flow.quote;

    // Keep name/mobile in sync when provider is prefilled (invalid selection =
    // controller not yet edited). Address sync is owned by BookingAddressField
    // (its listener would notifyListeners during build if we set .text here).
    if (_nameCtrl.text != flow.fullName && !_nameCtrl.selection.isValid) {
      _nameCtrl.text = flow.fullName;
    }
    if (_mobileCtrl.text != flow.mobile && !_mobileCtrl.selection.isValid) {
      _mobileCtrl.text = flow.mobile;
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F5),
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _buildHeader(context, height: widget.embeddedInShell ? 44 : 46),
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final dens = _densityFor(constraints.maxHeight);
                  final gap = dens.gap;
                  final fieldH = dens.fieldH;
                  final choiceH = dens.choiceH;
                  final planH = flow.isBedBugsPrimaryPlan || !flow.amcAvailable
                      ? choiceH + 4
                      : choiceH;
                  final keyboardOpen = MediaQuery.viewInsetsOf(context).bottom > 0;

                  return SingleChildScrollView(
                        // Scroll only as overflow safety (keyboard / very short phones).
                        physics: keyboardOpen || constraints.maxHeight < 560
                            ? const AlwaysScrollableScrollPhysics()
                            : const ClampingScrollPhysics(),
                        padding: EdgeInsets.fromLTRB(10, 0, 10, keyboardOpen ? 12 : 6),
                        child: ConstrainedBox(
                          constraints: BoxConstraints(minHeight: constraints.maxHeight - 2),
                          child: IntrinsicHeight(
                            child: Column(
                              children: [
                                _buildHero(dens),
                                Expanded(
                                  child: Container(
                                    width: double.infinity,
                                    padding: EdgeInsets.fromLTRB(
                                      dens.formPadH,
                                      dens.formPadV,
                                      dens.formPadH,
                                      dens.formPadV,
                                    ),
                                    decoration: const BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.vertical(bottom: Radius.circular(18)),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Color(0x17173B24),
                                          blurRadius: 30,
                                          offset: Offset(0, 12),
                                        ),
                                      ],
                                    ),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.stretch,
                                      children: [
                                        Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    'Confirm Your Booking',
                                                    style: TextStyle(
                                                      fontSize: dens.titleSize,
                                                      fontWeight: FontWeight.w800,
                                                      color: _navy,
                                                      height: 1.15,
                                                    ),
                                                  ),
                                                  Text(
                                                    '100% Service Warranty',
                                                    style: TextStyle(
                                                      fontSize: dens.warrantySize,
                                                      fontWeight: FontWeight.w700,
                                                      color: _navy.withValues(alpha: 0.85),
                                                      height: 1.15,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                            Padding(
                                              padding: const EdgeInsets.only(top: 2),
                                              child: Text(
                                                '* Required',
                                                style: TextStyle(
                                                  fontSize: dens.labelSize,
                                                  color: const Color(0xFF668071),
                                                  fontWeight: FontWeight.w600,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                        if (flow.ratesError != null) ...[
                                          SizedBox(height: gap),
                                          _banner(
                                            flow.ratesError!,
                                            Colors.amber.shade50,
                                            Colors.amber.shade900,
                                          ),
                                        ],
                                        if (_submitMessage != null) ...[
                                          SizedBox(height: gap),
                                          _banner(
                                            _submitMessage!,
                                            Colors.red.shade50,
                                            Colors.red.shade800,
                                          ),
                                        ],
                                        SizedBox(height: gap),
                                        _propToggle(flow, dens),
                                        SizedBox(height: gap),
                                        Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Expanded(child: _pestSelect(flow, dens)),
                                            SizedBox(width: dens.colGap),
                                            Expanded(
                                              child: flow.isResidential && flow.pestTypes.isNotEmpty
                                                  ? _premiseSelect(flow, dens)
                                                  : const SizedBox.shrink(),
                                            ),
                                          ],
                                        ),
                                        if (flow.isResidential && !flow.isInspectionQuote) ...[
                                          if (flow.showTreatmentQuality) ...[
                                            SizedBox(height: gap),
                                            _label('TREATMENT QUALITY *', dens),
                                            _choiceRow(
                                              dens: dens,
                                              children: [
                                                _choiceCard(
                                                  dens: dens,
                                                  title: 'Standard',
                                                  sub: 'Gel + spray',
                                                  selected: flow.treatmentQuality == 'standard',
                                                  height: choiceH,
                                                  onTap: () => flow.setTreatmentQuality('standard'),
                                                  onInfo: () => _showTreatmentInfo('standard'),
                                                ),
                                                _choiceCard(
                                                  dens: dens,
                                                  title: 'Premium',
                                                  sub: 'No-smell treatment',
                                                  selected: flow.treatmentQuality == 'premium',
                                                  recommended: true,
                                                  height: choiceH,
                                                  onTap: () => flow.setTreatmentQuality('premium'),
                                                  onInfo: () => _showTreatmentInfo('premium'),
                                                ),
                                              ],
                                            ),
                                            if (_errors['treatmentQuality'] != null)
                                              _fieldError(_errors['treatmentQuality']!),
                                          ],
                                          SizedBox(height: gap),
                                          _label('SERVICE PLAN *', dens),
                                          _choiceRow(
                                            dens: dens,
                                            children: [
                                              _choiceCard(
                                                dens: dens,
                                                title: flow.oneTimePlanTitle,
                                                sub: flow.oneTimePlanSub,
                                                selected: flow.serviceType == 'one-time',
                                                height: planH,
                                                onTap: () => flow.setServiceType('one-time'),
                                              ),
                                              _choiceCard(
                                                dens: dens,
                                                title: 'AMC — 3 Visits',
                                                sub: flow.amcAvailable
                                                    ? '12-month protection'
                                                    : BookingFlowProvider.amcUnavailableLabel,
                                                selected: flow.serviceType == 'amc',
                                                recommended: flow.amcAvailable,
                                                disabled: !flow.amcAvailable,
                                                unavailable: !flow.amcAvailable,
                                                showLock: !flow.amcAvailable,
                                                height: planH,
                                                onTap: () => flow.setServiceType('amc'),
                                              ),
                                            ],
                                          ),
                                          if (_errors['serviceType'] != null)
                                            _fieldError(_errors['serviceType']!),
                                        ],
                                        SizedBox(height: gap),
                                        _label('SERVICE ADDRESS *', dens),
                                        BookingAddressField(
                                          controller: _addressCtrl,
                                          height: fieldH,
                                          decoration: _inputDeco(
                                            'Area, building or full address',
                                            dens: dens,
                                            error: _errors['streetAddress'] != null,
                                          ),
                                          errorText: _errors['streetAddress'],
                                        ),
                                        SizedBox(height: gap),
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  _label('PREFERRED DATE *', dens),
                                                  SizedBox(
                                                    height: fieldH,
                                                    child: InkWell(
                                                      onTap: _pickDate,
                                                      borderRadius: BorderRadius.circular(8),
                                                      child: InputDecorator(
                                                        decoration: _inputDeco('', dens: dens),
                                                        child: Text(
                                                          flow.friendlyPreferredDate.isEmpty
                                                              ? 'Select date'
                                                              : flow.friendlyPreferredDate,
                                                          style: TextStyle(
                                                            fontSize: dens.fieldFont,
                                                            fontWeight: FontWeight.w700,
                                                            color: flow.friendlyPreferredDate.isEmpty
                                                                ? AppColors.textHint
                                                                : const Color(0xFF1B2A22),
                                                          ),
                                                        ),
                                                      ),
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                            SizedBox(width: dens.colGap),
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  _label('PREFERRED TIME *', dens),
                                                  SizedBox(
                                                    height: fieldH,
                                                    child: InkWell(
                                                      onTap: _pickTime,
                                                      borderRadius: BorderRadius.circular(8),
                                                      child: InputDecorator(
                                                        decoration: _inputDeco('', dens: dens).copyWith(
                                                          prefixIcon: Icon(
                                                            Icons.access_time,
                                                            size: dens.fieldH < 34 ? 14 : 15,
                                                            color: _green,
                                                          ),
                                                          prefixIconConstraints: BoxConstraints(
                                                            minWidth: dens.fieldH < 34 ? 28 : 30,
                                                            minHeight: dens.fieldH,
                                                          ),
                                                        ),
                                                        child: Text(
                                                          flow.preferredTime.isEmpty
                                                              ? 'Select time'
                                                              : BookingFlowProvider.formatFriendlyTime(
                                                                  flow.preferredTime,
                                                                ),
                                                          style: TextStyle(
                                                            fontSize: dens.fieldFont,
                                                            fontWeight: FontWeight.w700,
                                                          ),
                                                        ),
                                                      ),
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                          ],
                                        ),
                                        SizedBox(height: gap),
                                        Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Expanded(
                                              flex: 9,
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  _label('YOUR NAME *', dens),
                                                  SizedBox(
                                                    height: fieldH,
                                                    child: TextField(
                                                      controller: _nameCtrl,
                                                      onChanged: (value) {
                                                        flow.setFullName(value);
                                                        // setFullName collapses spaces / strips symbols —
                                                        // keep the field text aligned (website sanitize).
                                                        if (_nameCtrl.text != flow.fullName) {
                                                          _nameCtrl.value = TextEditingValue(
                                                            text: flow.fullName,
                                                            selection: TextSelection.collapsed(
                                                              offset: flow.fullName.length,
                                                            ),
                                                          );
                                                        }
                                                      },
                                                      keyboardType: TextInputType.name,
                                                      textCapitalization: TextCapitalization.words,
                                                      inputFormatters: [
                                                        FilteringTextInputFormatter.allow(
                                                          RegExp(r'[\p{L}\s]', unicode: true),
                                                        ),
                                                      ],
                                                      style: TextStyle(
                                                        fontSize: dens.fieldFont,
                                                        fontWeight: FontWeight.w700,
                                                      ),
                                                      decoration: _inputDeco(
                                                        'Full name',
                                                        dens: dens,
                                                        error: _errors['name'] != null,
                                                      ),
                                                    ),
                                                  ),
                                                  if (_errors['name'] != null)
                                                    _fieldError(_errors['name']!),
                                                ],
                                              ),
                                            ),
                                            SizedBox(width: dens.colGap),
                                            Expanded(
                                              flex: 11,
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  _label('MOBILE NUMBER *', dens),
                                                  SizedBox(
                                                    height: fieldH,
                                                    child: TextField(
                                                      controller: _mobileCtrl,
                                                      onChanged: flow.setMobile,
                                                      keyboardType: TextInputType.phone,
                                                      inputFormatters: [
                                                        FilteringTextInputFormatter.digitsOnly,
                                                        LengthLimitingTextInputFormatter(10),
                                                      ],
                                                      style: TextStyle(
                                                        fontSize: dens.fieldFont,
                                                        fontWeight: FontWeight.w700,
                                                      ),
                                                      decoration: _inputDeco(
                                                        '10 digits',
                                                        dens: dens,
                                                        error: _errors['phone'] != null,
                                                      ).copyWith(
                                                        prefixIcon: Padding(
                                                          padding: const EdgeInsets.only(
                                                            left: 6,
                                                            right: 2,
                                                          ),
                                                          child: Text(
                                                            '🇮🇳 +91',
                                                            style: TextStyle(
                                                              fontSize: dens.fieldFont - 0.5,
                                                              fontWeight: FontWeight.w800,
                                                            ),
                                                          ),
                                                        ),
                                                        prefixIconConstraints: BoxConstraints(
                                                          minWidth: dens.fieldH < 34 ? 48 : 52,
                                                          minHeight: dens.fieldH,
                                                        ),
                                                      ),
                                                    ),
                                                  ),
                                                  if (_errors['phone'] != null)
                                                    _fieldError(_errors['phone']!),
                                                ],
                                              ),
                                            ),
                                          ],
                                        ),
                                        const Spacer(),
                                        SizedBox(height: gap),
                                        // Guidelines live on success screen — keep form = website one-viewport CTA.
                                        _priceBar(flow, q, dens),
                                        SizedBox(height: dens.gap > 5 ? 6 : 5),
                                        SizedBox(
                                          height: dens.ctaH,
                                          child: FilledButton(
                                            style: FilledButton.styleFrom(
                                              backgroundColor: _green,
                                              foregroundColor: Colors.white,
                                              shape: RoundedRectangleBorder(
                                                borderRadius: BorderRadius.circular(11),
                                              ),
                                            ),
                                            onPressed: _busy || _otpSending ? null : _onConfirm,
                                            child: Text(
                                              _busy || _otpSending
                                                  ? 'Sending OTP…'
                                                  : flow.isOtherPremiseSize
                                                      ? 'Call / WhatsApp for Quote →'
                                                      : 'Confirm Booking →',
                                              style: TextStyle(
                                                fontWeight: FontWeight.w900,
                                                fontSize: dens.ctaFont,
                                              ),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                },
              ),
            ),
          ],
        ),
      ),
      bottomSheet: _otpOpen ? _otpSheet() : null,
    );
  }


  Widget _buildHeader(BuildContext context, {required double height}) {
    final embedded = widget.embeddedInShell;
    return Container(
      height: height,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Color(0xFFE8EEE9))),
      ),
      child: Row(
        children: [
          if (!embedded)
            IconButton(
              onPressed: () => context.canPop() ? context.pop() : context.go('/home'),
              icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18, color: _navy),
              visualDensity: VisualDensity.compact,
            )
          else
            const SizedBox(width: 4),
          Expanded(
            child: Text.rich(
              TextSpan(
                style: TextStyle(
                  fontSize: height < 46 ? 14.5 : 15.5,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.6,
                ),
                children: const [
                  TextSpan(text: 'PEST', style: TextStyle(color: _navy)),
                  TextSpan(text: 'CONTROL', style: TextStyle(color: _green)),
                  TextSpan(text: '99', style: TextStyle(color: _navy)),
                  TextSpan(
                    text: '.COM',
                    style: TextStyle(
                      color: _navy,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
                    ),
                  ),
                ],
              ),
              textAlign: embedded ? TextAlign.left : TextAlign.center,
            ),
          ),
          if (!embedded) const SizedBox(width: 40) else const SizedBox(width: 4),
        ],
      ),
    );
  }

  Widget _buildHero(_FormDensity dens) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(12, dens.heroPadV, 12, dens.heroPadV),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFFE5F8EB), Color(0xFFCCEBD5)],
          stops: [0.68, 1],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
              color: _green,
              borderRadius: BorderRadius.circular(5),
            ),
            child: const Text(
              'LICENSED PEST CONTROL',
              style: TextStyle(
                color: Colors.white,
                fontSize: 8,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
          ),
          SizedBox(height: dens.gap > 5 ? 4 : 3),
          Text.rich(
            TextSpan(
              style: TextStyle(
                fontSize: dens.heroTitle,
                fontWeight: FontWeight.w800,
                height: 1.05,
                letterSpacing: -0.8,
                color: _navy,
              ),
              children: const [
                TextSpan(text: 'Book Pest Control '),
                TextSpan(text: 'in 60 Seconds', style: TextStyle(color: _green)),
              ],
            ),
          ),
          if (dens.showTrust) ...[
            const SizedBox(height: 3),
            const Text(
              'Verified Experts • Branded Chemicals • Invoice',
              style: TextStyle(
                fontSize: 9.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF365244),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _propToggle(BookingFlowProvider flow, _FormDensity dens) {
    return Container(
      height: dens.propH + 4,
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: const Color(0xFFEDF5F0),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: _tabBtn(
              label: '🏠 Residential',
              active: flow.isResidential,
              height: dens.propH,
              fontSize: dens.fieldH < 34 ? 10 : 11,
              onTap: () => flow.setPremiseType('residential'),
            ),
          ),
          Expanded(
            child: _tabBtn(
              label: '🏢 Commercial',
              active: flow.isCommercial,
              height: dens.propH,
              fontSize: dens.fieldH < 34 ? 10 : 11,
              onTap: () => flow.setPremiseType('commercial'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _tabBtn({
    required String label,
    required bool active,
    required VoidCallback onTap,
    double height = 28,
    double fontSize = 11,
  }) {
    return Material(
      color: active ? _green : Colors.transparent,
      borderRadius: BorderRadius.circular(7),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(7),
        child: SizedBox(
          height: height,
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontSize: fontSize,
                fontWeight: FontWeight.w800,
                color: active ? Colors.white : const Color(0xFF547061),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _pestSelect(BookingFlowProvider flow, _FormDensity dens) {
    final label = flow.pestTypes.isEmpty
        ? 'Select service'
        : flow.pestTypes.length == 1
            ? (BookingFlowProvider.pestOptions
                    .where((p) => p.value == flow.pestTypes.first)
                    .map((p) => p.label)
                    .firstOrNull ??
                flow.pestTypes.first)
            : '${flow.pestTypes.length} services selected';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label('SELECT SERVICE *', dens),
        SizedBox(
          height: dens.fieldH,
          child: PopupMenuButton<String>(
            onSelected: (v) {
              if (flow.pestTypes.contains(v)) {
                if (flow.pestTypes.length > 1) flow.togglePest(v);
              } else {
                flow.togglePest(v);
              }
            },
            itemBuilder: (_) => BookingFlowProvider.pestOptions
                .map(
                  (p) => CheckedPopupMenuItem<String>(
                    value: p.value,
                    checked: flow.pestTypes.contains(p.value),
                    child: Text(p.label),
                  ),
                )
                .toList(),
            child: InputDecorator(
              decoration: _inputDeco('', dens: dens),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: dens.fieldFont,
                        fontWeight: FontWeight.w700,
                        color: flow.pestTypes.isEmpty ? AppColors.textHint : const Color(0xFF1B2A22),
                      ),
                    ),
                  ),
                  Icon(Icons.keyboard_arrow_down, size: dens.fieldH < 34 ? 16 : 18, color: _green),
                ],
              ),
            ),
          ),
        ),
        if (_errors['pestTypes'] != null) _fieldError(_errors['pestTypes']!),
      ],
    );
  }

  Widget _premiseSelect(BookingFlowProvider flow, _FormDensity dens) {
    final selected = BookingFlowProvider.premiseSizeOptions
        .where((o) => o.value == flow.premiseSize)
        .map((o) => o.label)
        .firstOrNull;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label('PREMISE SIZE *', dens),
        SizedBox(
          height: dens.fieldH,
          child: PopupMenuButton<String>(
            onSelected: (v) {
              flow.setPremiseSize(v);
              if (v == 'other') _openOtherPremiseHelp();
            },
            itemBuilder: (_) => BookingFlowProvider.premiseSizeOptions
                .map((o) => PopupMenuItem(value: o.value, child: Text(o.label)))
                .toList(),
            child: InputDecorator(
              decoration: _inputDeco('', dens: dens, error: _errors['premiseSize'] != null),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      selected ?? 'Select size',
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: dens.fieldFont,
                        fontWeight: FontWeight.w700,
                        color: selected == null ? AppColors.textHint : const Color(0xFF1B2A22),
                      ),
                    ),
                  ),
                  Icon(Icons.keyboard_arrow_down, size: dens.fieldH < 34 ? 16 : 18, color: _green),
                ],
              ),
            ),
          ),
        ),
        if (_errors['premiseSize'] != null) _fieldError(_errors['premiseSize']!),
      ],
    );
  }

  Widget _choiceRow({required _FormDensity dens, required List<Widget> children}) {
    return Row(
      children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0) SizedBox(width: dens.colGap),
          Expanded(child: children[i]),
        ],
      ],
    );
  }

  Widget _choiceCard({
    required _FormDensity dens,
    required String title,
    required String sub,
    required bool selected,
    required double height,
    required VoidCallback onTap,
    VoidCallback? onInfo,
    bool recommended = false,
    bool disabled = false,
    bool unavailable = false,
    bool showLock = false,
  }) {
    return Opacity(
      opacity: disabled ? 0.78 : 1,
      child: Material(
        color: selected
            ? _soft
            : (disabled ? const Color(0xFFF5F7F6) : Colors.white),
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          onTap: disabled ? null : onTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            height: height,
            padding: EdgeInsets.fromLTRB(dens.fieldH < 34 ? 6 : 7, 2, dens.fieldH < 34 ? 6 : 7, 2),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: selected
                    ? _green
                    : (disabled ? const Color(0xFFD5DDD8) : _line),
                width: 1.5,
              ),
            ),
            child: Stack(
              children: [
                if (recommended && !disabled)
                  Positioned(
                    right: 0,
                    top: 0,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE99C16),
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: const Text(
                        'BEST VALUE',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 6,
                          fontWeight: FontWeight.w900,
                          height: 1.1,
                        ),
                      ),
                    ),
                  ),
                if (unavailable)
                  Positioned(
                    right: 0,
                    top: 0,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6C7F74),
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: const Text(
                        BookingFlowProvider.amcUnavailableBadge,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 6,
                          fontWeight: FontWeight.w900,
                          height: 1.1,
                        ),
                      ),
                    ),
                  ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      children: [
                        if (showLock) ...[
                          const Icon(Icons.lock_outline, size: 11, color: Color(0xFF6C7F74)),
                          const SizedBox(width: 2),
                        ],
                        Expanded(
                          child: Text(
                            title,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: dens.choiceTitle,
                              fontWeight: FontWeight.w800,
                              height: 1.1,
                              color: disabled ? const Color(0xFF6C7F74) : const Color(0xFF1B2A22),
                            ),
                          ),
                        ),
                      ],
                    ),
                    Text(
                      sub,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: dens.choiceSub,
                        color: const Color(0xFF6C7F74),
                        height: 1.1,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                if (onInfo != null)
                  Positioned(
                    right: 0,
                    bottom: 0,
                    child: GestureDetector(
                      onTap: onInfo,
                      child: Container(
                        width: dens.fieldH < 34 ? 14 : 16,
                        height: dens.fieldH < 34 ? 14 : 16,
                        decoration: const BoxDecoration(
                          color: Color(0xFFDFF3E6),
                          shape: BoxShape.circle,
                        ),
                        alignment: Alignment.center,
                        child: Text(
                          'i',
                          style: TextStyle(
                            color: _green,
                            fontSize: dens.fieldH < 34 ? 9 : 10,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _priceBar(BookingFlowProvider flow, QuotePriceResult q, _FormDensity dens) {
    final showPromo = flow.selectionsComplete &&
        !flow.isInspectionQuote &&
        !q.pricePending &&
        !flow.ratesLoading &&
        q.offerPrice > 0 &&
        q.listPrice > q.offerPrice &&
        q.discountPercent > 0;

    final amountSize = dens.priceH < 34 ? 16.0 : 17.0;

    Widget amount;
    if (flow.ratesLoading) {
      amount = Text('…', style: TextStyle(fontWeight: FontWeight.w900, fontSize: amountSize, color: _navy));
    } else if (flow.isInspectionQuote) {
      amount = Text(
        'Free visit',
        style: TextStyle(fontWeight: FontWeight.w900, fontSize: amountSize - 1, color: _navy),
      );
    } else if (showPromo) {
      amount = Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            BookingFlowProvider.formatInr(q.listPrice),
            style: const TextStyle(
              fontSize: 11,
              color: Color(0xFF819087),
              decoration: TextDecoration.lineThrough,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 5),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            decoration: BoxDecoration(
              color: const Color(0xFFE06A13),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              '${q.discountPercent}% OFF',
              style: const TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.w900),
            ),
          ),
          const SizedBox(width: 5),
          Text(
            BookingFlowProvider.formatInr(q.offerPrice),
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: amountSize, color: _navy),
          ),
        ],
      );
    } else if (flow.selectionsComplete && !q.pricePending && q.offerPrice > 0) {
      amount = Text(
        BookingFlowProvider.formatInr(q.offerPrice),
        style: TextStyle(fontWeight: FontWeight.w900, fontSize: amountSize, color: _navy),
      );
    } else if (flow.selectionsComplete && q.pricePending) {
      amount = Text(
        'On request',
        style: TextStyle(fontWeight: FontWeight.w900, fontSize: amountSize - 1, color: _navy),
      );
    } else {
      amount = Text('₹0', style: TextStyle(fontWeight: FontWeight.w900, fontSize: amountSize, color: _navy));
    }

    return Container(
      height: dens.priceH,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        gradient: const LinearGradient(colors: [Color(0xFFEFFAF3), Color(0xFFE5F6EB)]),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  flow.priceSummaryLabel,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 10,
                    color: Color(0xFF537060),
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (flow.selectionsComplete &&
                    !flow.isInspectionQuote &&
                    !q.pricePending &&
                    q.offerPrice > 0)
                  const Text(
                    'Price (Excluding GST)',
                    style: TextStyle(fontSize: 8.5, color: Color(0xFFE06A13), fontWeight: FontWeight.w800),
                  )
                else if (flow.selectionsComplete && q.pricePending && !flow.isInspectionQuote)
                  const Text(
                    'Price confirmation pending',
                    style: TextStyle(fontSize: 8.5, color: Color(0xFFE06A13), fontWeight: FontWeight.w800),
                  ),
              ],
            ),
          ),
          amount,
        ],
      ),
    );
  }

  Widget _otpSheet() {
    return Material(
      elevation: 12,
      color: Colors.white,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          18,
          20,
          18 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Verify mobile number',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: _navy),
                  ),
                ),
                IconButton(
                  onPressed: _otpVerifying
                      ? null
                      : () => setState(() {
                            _otpOpen = false;
                          }),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            Text(
              'OTP sent to +91 ${_otpMobile.isNotEmpty ? _otpMobile : context.read<BookingFlowProvider>().mobile} to confirm your booking.',
              style: const TextStyle(fontSize: 13, color: AppColors.textMuted, height: 1.35),
            ),
            const SizedBox(height: 6),
            const Text(
              'OTP will be sent to your WhatsApp number. Please check WhatsApp only.',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFFC62828)),
            ),
            if (_otpHint.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(_otpHint, style: const TextStyle(fontSize: 12, color: _green, fontWeight: FontWeight.w700)),
            ],
            const SizedBox(height: 12),
            TextField(
              controller: _otpCtrl,
              keyboardType: TextInputType.number,
              maxLength: 4,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 8),
              decoration: _inputDeco(
                'OTP',
                dens: const _FormDensity(
                  gap: 6,
                  colGap: 7,
                  fieldH: 40,
                  choiceH: 38,
                  propH: 28,
                  priceH: 36,
                  ctaH: 42,
                  headerH: 46,
                  formPadH: 10,
                  formPadV: 8,
                  titleSize: 15,
                  warrantySize: 10,
                  labelSize: 9,
                  fieldFont: 14,
                  choiceTitle: 11,
                  choiceSub: 8,
                  ctaFont: 14.5,
                  showTrust: true,
                  heroPadV: 8,
                  heroTitle: 18,
                ),
              ).copyWith(counterText: ''),
              enabled: !_otpVerifying,
              onChanged: (_) {
                if (_otpError.isNotEmpty) {
                  setState(() => _otpError = '');
                } else {
                  setState(() {});
                }
              },
              onSubmitted: (_) {
                if (_otpCtrl.text.replaceAll(RegExp(r'\D'), '').length == 4) {
                  _verifyAndCreate();
                }
              },
            ),
            if (_otpError.isNotEmpty) _fieldError(_otpError),
            const SizedBox(height: 10),
            FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: _green,
                minimumSize: const Size.fromHeight(46),
              ),
              onPressed: _otpVerifying || _otpSending || _otpCtrl.text.replaceAll(RegExp(r'\D'), '').length != 4
                  ? null
                  : _verifyAndCreate,
              child: Text(_otpVerifying ? 'Confirming booking…' : 'Verify & Confirm Booking'),
            ),
            TextButton(
              onPressed: _resendCooldown > 0 || _otpSending || _otpVerifying ? null : _resendOtp,
              child: Text(
                _otpSending
                    ? 'Sending…'
                    : _resendCooldown > 0
                        ? 'Resend OTP in ${_resendCooldown}s'
                        : 'Resend OTP',
              ),
            ),
          ],
        ),
      ),
    );
  }

  InputDecoration _inputDeco(String hint, {required _FormDensity dens, bool error = false}) {
    return InputDecoration(
      hintText: hint.isEmpty ? null : hint,
      hintStyle: TextStyle(
        fontSize: dens.fieldFont,
        fontWeight: FontWeight.w500,
        color: const Color(0xFF9DAAA3),
      ),
      filled: true,
      fillColor: Colors.white,
      isDense: true,
      contentPadding: EdgeInsets.symmetric(horizontal: dens.fieldH < 34 ? 8 : 9, vertical: 0),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: error ? Colors.red.shade400 : _line, width: 1.5),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: error ? Colors.red.shade400 : _line, width: 1.5),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: _green, width: 1.6),
      ),
    );
  }

  Widget _label(String text, _FormDensity dens) => Padding(
        padding: EdgeInsets.only(bottom: dens.gap > 5 ? 2 : 1),
        child: Text(
          text,
          style: TextStyle(
            fontSize: dens.labelSize,
            fontWeight: FontWeight.w800,
            color: const Color(0xFF4B6255),
            letterSpacing: 0.02,
            height: 1.1,
          ),
        ),
      );

  Widget _fieldError(String text) => Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Text(text, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.red)),
      );

  Widget _banner(String text, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(text, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: fg)),
      );
}

/// Website-aligned spacing / type scale for the one-viewport booking form.
class _FormDensity {
  const _FormDensity({
    required this.gap,
    required this.colGap,
    required this.fieldH,
    required this.choiceH,
    required this.propH,
    required this.priceH,
    required this.ctaH,
    required this.headerH,
    required this.formPadH,
    required this.formPadV,
    required this.titleSize,
    required this.warrantySize,
    required this.labelSize,
    required this.fieldFont,
    required this.choiceTitle,
    required this.choiceSub,
    required this.ctaFont,
    required this.showTrust,
    required this.heroPadV,
    required this.heroTitle,
  });

  final double gap;
  final double colGap;
  final double fieldH;
  final double choiceH;
  final double propH;
  final double priceH;
  final double ctaH;
  final double headerH;
  final double formPadH;
  final double formPadV;
  final double titleSize;
  final double warrantySize;
  final double labelSize;
  final double fieldFont;
  final double choiceTitle;
  final double choiceSub;
  final double ctaFont;
  final bool showTrust;
  final double heroPadV;
  final double heroTitle;
}

/// Kept for route compatibility — redirects handled in router; this is the success screen.
class BookingConfirmedScreen extends StatelessWidget {
  const BookingConfirmedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final booking = flow.confirmedBooking;
    final id = booking?.code ??
        'BK-${DateFormat('yyMMdd').format(DateTime.now())}${booking?.id ?? 1578}';
    final mobile = flow.confirmedMobile ??
        context.watch<AuthProvider>().profile?.mobile ??
        '—';

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
              decoration: const BoxDecoration(color: Color(0xFF087B3D), shape: BoxShape.circle),
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
            booking?.priceConfirmationPending == true
                ? 'Final price will be shared after confirmation'
                : 'Our team will contact you to confirm the service',
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
                    Expanded(
                      child: Text(id, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
                    ),
                    IconButton(
                      onPressed: () => pc99Copy(context, id, label: 'Booking ID copied'),
                      icon: const Icon(Icons.copy_rounded, color: AppColors.textSecondary),
                    ),
                  ],
                ),
                const Divider(color: AppColors.divider),
                const Text(
                  'We have sent the details to your',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
                const SizedBox(height: 4),
                Text('+91 $mobile', style: const TextStyle(fontWeight: FontWeight.w800)),
              ],
            ),
          ),
          const SizedBox(height: 16),
          ServiceGuidelinesCard(
            treatmentQuality: flow.treatmentQuality.isEmpty ? null : flow.treatmentQuality,
            title: "After booking — Do's & Don'ts",
          ),
          const SizedBox(height: 20),
          Pc99PrimaryButton(label: 'Back to Home', onPressed: () => context.go('/home')),
        ],
      ),
    );
  }
}

// Legacy aliases so any remaining imports still compile during the cutover.
@Deprecated('Use WebsiteBookingScreen')
typedef PropertySelectionScreen = WebsiteBookingScreen;

@Deprecated('Use WebsiteBookingScreen')
class DateTimeSelectionScreen extends StatelessWidget {
  const DateTimeSelectionScreen({super.key});
  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (context.mounted) context.go('/book');
    });
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}

@Deprecated('Use WebsiteBookingScreen')
class BookingSummaryScreen extends StatelessWidget {
  const BookingSummaryScreen({super.key});
  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (context.mounted) context.go('/book');
    });
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
