import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/api_config.dart';
import '../core/api_client.dart';
import '../core/booking_form_density.dart';
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
  final _otpFocus = FocusNode();
  final String _bookingSessionId = _newBookingSessionId();

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
      flow.setRatesError(
        '$e'.contains('DioException') ? ApiClient.offlineMessage : '$e',
      );
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _addressCtrl.dispose();
    _otpCtrl.dispose();
    _otpFocus.dispose();
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

  static String _newBookingSessionId() {
    final rand = math.Random();
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    return List.generate(24, (_) => chars[rand.nextInt(chars.length)]).join();
  }

  String _customerMessage(Object error) {
    final text = '$error';
    if (text.contains('DioException') || text.contains('SocketException')) {
      return ApiClient.offlineMessage;
    }
    return text;
  }

  Future<void> _onConfirm() async {
    if (_busy || _otpSending || _otpVerifying) return;
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
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _otpFocus.requestFocus();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitMessage = _customerMessage(e));
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
      setState(() => _otpError = _customerMessage(e));
    } finally {
      if (mounted) setState(() => _otpSending = false);
    }
  }

  Future<void> _verifyAndCreate() async {
    if (_otpVerifying || _otpSending) return;
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
        bookingSessionId: _bookingSessionId,
        bookingSource: 'APP',
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
      setState(() => _otpError = _customerMessage(e));
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

  BookingFormDensity _densityFor({
    required double bodyHeight,
    required double contentWidth,
    required BookingFormShape shape,
    required double bottomPad,
  }) {
    return BookingFormDensity.fit(
      bodyHeight: bodyHeight,
      contentWidth: contentWidth,
      shape: shape,
      bottomPad: bottomPad,
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
            _buildHeader(
              context,
              height: widget.embeddedInShell ? 48 : 52,
            ),
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final view = View.of(context);
                  final dpr = view.devicePixelRatio == 0
                      ? 1.0
                      : view.devicePixelRatio;
                  final rawKeyboard = view.viewInsets.bottom / dpr;
                  final mqKeyboard = MediaQuery.viewInsetsOf(context).bottom;
                  // Scaffold consumes viewInsets when it resizes. Add the raw
                  // inset back so density stays on the full page and the form
                  // scrolls instead of crushing while the keyboard is open.
                  final fitHeight = constraints.maxHeight +
                      (mqKeyboard == 0 ? rawKeyboard : 0);
                  final bottomPad = widget.embeddedInShell ? 2.0 : 4.0;
                  final contentWidth = constraints.maxWidth -
                      20 -
                      BookingFormDensity.sheet.formPadH * 2;
                  final residentialQuote =
                      flow.isResidential && !flow.isInspectionQuote;
                  final shape = BookingFormShape(
                    showTreatment:
                        residentialQuote && flow.showTreatmentQuality,
                    showPlan: residentialQuote,
                    planTaller:
                        flow.isBedBugsPrimaryPlan || !flow.amcAvailable,
                    banners: (flow.ratesError != null ? 1 : 0) +
                        (_submitMessage != null ? 1 : 0),
                  );
                  final dens = _densityFor(
                    bodyHeight: fitHeight,
                    contentWidth: contentWidth,
                    shape: shape,
                    bottomPad: bottomPad,
                  );
                  final gap = dens.gap;
                  final inputH = dens.inputH;
                  final choiceH = dens.choiceH;
                  final planH = dens.planHeight(shape);

                  List<Widget> formFields() => [
                        _titleRow(dens),
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
                          height: inputH,
                          decoration: _borderlessDeco(
                            'Area, building or full address',
                            dens: dens,
                          ),
                          errorText: _errors['streetAddress'],
                          errorBorder: _errors['streetAddress'] != null,
                        ),
                        SizedBox(height: gap),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  _label('PREFERRED DATE *', dens),
                                  _scheduleTapField(
                                    dens: dens,
                                    height: inputH,
                                    onTap: _pickDate,
                                    child: Text(
                                      flow.friendlyPreferredDate.isEmpty
                                          ? 'Select date'
                                          : flow.friendlyPreferredDate,
                                      maxLines: 1,
                                      softWrap: false,
                                      style: TextStyle(
                                        fontSize: dens.inputFont,
                                        fontWeight: FontWeight.w700,
                                        color: flow.friendlyPreferredDate.isEmpty
                                            ? const Color(0xFF9DAAA3)
                                            : const Color(0xFF1B2A22),
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
                                  _scheduleTapField(
                                    dens: dens,
                                    height: inputH,
                                    onTap: _pickTime,
                                    prefix: Icon(
                                      Icons.access_time,
                                      size: inputH < 36 ? 14 : 16,
                                      color: _green,
                                    ),
                                    child: Text(
                                      flow.preferredTime.isEmpty
                                          ? 'Select time'
                                          : BookingFlowProvider.formatFriendlyTime(
                                              flow.preferredTime,
                                            ),
                                      maxLines: 1,
                                      softWrap: false,
                                      style: TextStyle(
                                        fontSize: dens.inputFont,
                                        fontWeight: FontWeight.w700,
                                        color: const Color(0xFF1B2A22),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: gap),
                        // Website `.booking-grid-phone`: 0.9fr / 1.1fr — equal HEIGHT.
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 8,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  _label('YOUR NAME *', dens),
                                  _boxedInput(
                                    height: inputH,
                                    error: _errors['name'] != null,
                                    child: TextField(
                                      controller: _nameCtrl,
                                      onChanged: (value) {
                                        flow.setFullName(value);
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
                                      textAlignVertical: TextAlignVertical.center,
                                      inputFormatters: [
                                        FilteringTextInputFormatter.allow(
                                          RegExp(r'[\p{L}\s]', unicode: true),
                                        ),
                                      ],
                                      style: TextStyle(
                                        fontSize: dens.inputFont,
                                        fontWeight: FontWeight.w700,
                                        height: 1.2,
                                        color: const Color(0xFF1B2A22),
                                      ),
                                      decoration: _borderlessDeco(
                                        'Full name',
                                        dens: dens,
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
                              flex: 12,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  _label('MOBILE NUMBER *', dens),
                                  _phoneField(
                                    dens: dens,
                                    height: inputH,
                                    error: _errors['phone'] != null,
                                    onChanged: flow.setMobile,
                                  ),
                                  if (_errors['phone'] != null)
                                    _fieldError(_errors['phone']!),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ];

                  Widget priceAndCta() => Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          SizedBox(height: dens.ctaGap),
                          _priceBar(flow, q, dens),
                          SizedBox(height: dens.ctaGap),
                          SizedBox(
                            height: dens.ctaH,
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(11),
                                gradient: const LinearGradient(
                                  colors: [Color(0xFF087B3D), Color(0xFF15984E)],
                                ),
                                boxShadow: const [
                                  BoxShadow(
                                    color: Color(0x38087B3D),
                                    blurRadius: 14,
                                    offset: Offset(0, 6),
                                  ),
                                ],
                              ),
                              child: Material(
                                color: Colors.transparent,
                                child: InkWell(
                                  onTap: _busy || _otpSending || _otpVerifying
                                      ? null
                                      : _onConfirm,
                                  borderRadius: BorderRadius.circular(11),
                                  child: Center(
                                    child: Text(
                                      _busy || _otpSending
                                          ? 'Sending OTP...'
                                          : flow.isOtherPremiseSize
                                              ? 'Call / WhatsApp for Quote →'
                                              : 'Confirm Booking →',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w900,
                                        fontSize: dens.ctaFont,
                                        color: Colors.white,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      );

                  return Padding(
                    padding: EdgeInsets.fromLTRB(10, 0, 10, bottomPad),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _buildHero(dens),
                        Expanded(
                          child: Container(
                            width: double.infinity,
                            padding: EdgeInsets.fromLTRB(
                              dens.formPadH,
                              dens.formPadV,
                              dens.formPadH,
                              dens.cardBottom,
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
                            // Scroll is only a safety valve (very short screens, keyboard,
                            // or a validation banner). A fitted page does not move.
                            child: SingleChildScrollView(
                              physics: const ClampingScrollPhysics(),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  ...formFields(),
                                  priceAndCta(),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
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
    // Website `.site-header-logo`: left, ~36px mobile / ~48px desktop, contain.
    final logoHeight = embedded ? 36.0 : 40.0;
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
            const SizedBox(width: 2),
          Pc99Logo(height: logoHeight),
          const Spacer(),
        ],
      ),
    );
  }

  Widget _buildHero(BookingFormDensity dens) {
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
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            heightFactor: 1,
            child: Container(
              height: BookingFormDensity.badgeH,
              padding: const EdgeInsets.symmetric(horizontal: 7),
              decoration: BoxDecoration(
                color: _green,
                borderRadius: BorderRadius.circular(5),
              ),
              alignment: Alignment.center,
              child: const Text(
                'LICENSED PEST CONTROL',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 8,
                  height: 1,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ),
          const SizedBox(height: BookingFormDensity.afterBadge),
          SizedBox(
            height: dens.heroTitle * 1.05,
            child: FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text.rich(
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
                maxLines: 1,
              ),
            ),
          ),
          if (dens.showTrust) ...[
            const SizedBox(height: BookingFormDensity.trustGap),
            const SizedBox(
              height: BookingFormDensity.trustH,
              child: Text(
                'Verified Experts • Branded Chemicals • Invoice',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 9.5,
                  height: 1,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF365244),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// Title and warranty stay on one line. Warranty scales down on narrow
  /// phones instead of wrapping "Confirm Your Booking".
  Widget _titleRow(BookingFormDensity dens) {
    return SizedBox(
      height: dens.titleLine,
      child: Row(
        children: [
          Expanded(
            child: FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Confirm Your Booking',
                    maxLines: 1,
                    softWrap: false,
                    style: TextStyle(
                      fontSize: dens.titleSize,
                      fontWeight: FontWeight.w800,
                      color: _navy,
                      height: 1.15,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '100% Service Warranty',
                    maxLines: 1,
                    softWrap: false,
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
          ),
          const SizedBox(width: 8),
          Text(
            '* Required',
            maxLines: 1,
            softWrap: false,
            style: TextStyle(
              fontSize: dens.labelSize,
              color: const Color(0xFF668071),
              fontWeight: FontWeight.w600,
              height: 1.1,
            ),
          ),
        ],
      ),
    );
  }

  Widget _propToggle(BookingFlowProvider flow, BookingFormDensity dens) {
    // Website `.booking-prop-toggle` padding 2 + `.booking-prop-btn` height.
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
              fontSize: 11,
              onTap: () => flow.setPremiseType('residential'),
            ),
          ),
          Expanded(
            child: _tabBtn(
              label: '🏢 Commercial',
              active: flow.isCommercial,
              height: dens.propH,
              fontSize: 11,
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

  Widget _pestSelect(BookingFlowProvider flow, BookingFormDensity dens) {
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
          height: dens.selectH,
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
            child: _boxedShell(
              height: dens.selectH,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 7),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        label,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: dens.selectFont,
                          fontWeight: FontWeight.w800,
                          color: flow.pestTypes.isEmpty
                              ? const Color(0xFF9DAAA3)
                              : const Color(0xFF1B2A22),
                        ),
                      ),
                    ),
                    const Icon(Icons.keyboard_arrow_down, size: 14, color: _green),
                  ],
                ),
              ),
            ),
          ),
        ),
        if (_errors['pestTypes'] != null) _fieldError(_errors['pestTypes']!),
      ],
    );
  }

  Widget _premiseSelect(BookingFlowProvider flow, BookingFormDensity dens) {
    final selected = BookingFlowProvider.premiseSizeOptions
        .where((o) => o.value == flow.premiseSize)
        .map((o) => o.label)
        .firstOrNull;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label('PREMISE SIZE *', dens),
        SizedBox(
          height: dens.selectH,
          child: PopupMenuButton<String>(
            onSelected: (v) {
              flow.setPremiseSize(v);
              if (v == 'other') _openOtherPremiseHelp();
            },
            itemBuilder: (_) => BookingFlowProvider.premiseSizeOptions
                .map((o) => PopupMenuItem(value: o.value, child: Text(o.label)))
                .toList(),
            child: _boxedShell(
              height: dens.selectH,
              error: _errors['premiseSize'] != null,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 7),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        selected ?? 'Select size',
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: dens.selectFont,
                          fontWeight: FontWeight.w800,
                          color: selected == null
                              ? const Color(0xFF9DAAA3)
                              : const Color(0xFF1B2A22),
                        ),
                      ),
                    ),
                    const Icon(Icons.keyboard_arrow_down, size: 14, color: _green),
                  ],
                ),
              ),
            ),
          ),
        ),
        if (_errors['premiseSize'] != null) _fieldError(_errors['premiseSize']!),
      ],
    );
  }

  Widget _choiceRow({required BookingFormDensity dens, required List<Widget> children}) {
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
    required BookingFormDensity dens,
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
            padding: const EdgeInsets.fromLTRB(7, 3, 7, 3),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: selected
                    ? _green
                    : (disabled ? const Color(0xFFD5DDD8) : _line),
                // Website: 1.5px + inset ring when selected.
                width: selected ? 2 : 1.5,
              ),
            ),
            child: Stack(
              clipBehavior: Clip.none,
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
                          letterSpacing: 0.02,
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
                        width: 16,
                        height: 16,
                        decoration: const BoxDecoration(
                          color: Color(0xFFDFF3E6),
                          shape: BoxShape.circle,
                        ),
                        alignment: Alignment.center,
                        child: const Text(
                          'i',
                          style: TextStyle(
                            color: _green,
                            fontSize: 10,
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

  Widget _priceBar(BookingFlowProvider flow, QuotePriceResult q, BookingFormDensity dens) {
    final showPromo = flow.selectionsComplete &&
        !flow.isInspectionQuote &&
        !q.pricePending &&
        !flow.ratesLoading &&
        q.offerPrice > 0 &&
        q.listPrice > q.offerPrice &&
        q.discountPercent > 0;

    final amountSize = 17.0;

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
                    fontSize: 9,
                    color: Color(0xFF537060),
                    fontWeight: FontWeight.w600,
                    height: 1.15,
                  ),
                ),
                if (flow.selectionsComplete &&
                    !flow.isInspectionQuote &&
                    !q.pricePending &&
                    q.offerPrice > 0)
                  const Text(
                    'Price (Excluding GST)',
                    style: TextStyle(fontSize: 9, color: Color(0xFFE06A13), fontWeight: FontWeight.w800),
                  )
                else if (flow.selectionsComplete && q.pricePending && !flow.isInspectionQuote)
                  const Text(
                    'Price confirmation pending',
                    style: TextStyle(fontSize: 9, color: Color(0xFFE06A13), fontWeight: FontWeight.w800),
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
              _otpSending
                  ? 'Sending OTP...'
                  : 'OTP sent to your WhatsApp number.',
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, height: 1.35),
            ),
            const SizedBox(height: 4),
            Text(
              'Sent to +91 ${_otpMobile.isNotEmpty ? _otpMobile : context.read<BookingFlowProvider>().mobile}. Check WhatsApp only.',
              style: const TextStyle(fontSize: 13, color: AppColors.textMuted, height: 1.35),
            ),
            if (_otpHint.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(_otpHint, style: const TextStyle(fontSize: 12, color: _green, fontWeight: FontWeight.w700)),
            ],
            const SizedBox(height: 14),
            _otpDigitBoxes(),
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
              child: Text(_otpVerifying ? 'Confirming booking…' : 'Verify'),
            ),
            TextButton(
              onPressed: _resendCooldown > 0 || _otpSending || _otpVerifying ? null : _resendOtp,
              child: Text(
                _otpSending
                    ? 'Sending OTP...'
                    : _resendCooldown > 0
                        ? 'Resend in ${_resendCooldown}s'
                        : 'Resend',
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _otpDigitBoxes() {
    final digits = _otpCtrl.text.replaceAll(RegExp(r'\D'), '');
    return Stack(
      alignment: Alignment.center,
      children: [
        Row(
          children: [
            for (var i = 0; i < 4; i++)
              Expanded(
                child: Container(
                  height: 52,
                  margin: EdgeInsets.only(left: i == 0 ? 0 : 8),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: _otpError.isNotEmpty ? Colors.red.shade400 : _line,
                      width: 1.5,
                    ),
                  ),
                  child: Text(
                    i < digits.length ? digits[i] : '',
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF1B2A22),
                    ),
                  ),
                ),
              ),
          ],
        ),
        TextField(
          controller: _otpCtrl,
          focusNode: _otpFocus,
          keyboardType: TextInputType.number,
          maxLength: 4,
          enabled: !_otpVerifying,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          showCursor: false,
          style: const TextStyle(color: Colors.transparent, fontSize: 1),
          // Theme InputDecoration fills and outlines the focused field.
          // That paint covers the four digit boxes and draws one bar.
          decoration: const InputDecoration(
            counterText: '',
            filled: false,
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
            disabledBorder: InputBorder.none,
            errorBorder: InputBorder.none,
            focusedErrorBorder: InputBorder.none,
            contentPadding: EdgeInsets.zero,
            isCollapsed: true,
          ),
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
      ],
    );
  }

  /// Outlined field chrome for OTP sheet (keeps Material outline borders).
  InputDecoration _inputDeco(String hint, {required BookingFormDensity dens, bool error = false}) {
    return InputDecoration(
      hintText: hint.isEmpty ? null : hint,
      hintStyle: TextStyle(
        fontSize: dens.inputFont,
        fontWeight: FontWeight.w500,
        color: const Color(0xFF9DAAA3),
        height: 1.2,
      ),
      filled: true,
      fillColor: Colors.white,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
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

  /// Borderless deco for TextFields hosted inside `_boxedInput` / address shell.
  InputDecoration _borderlessDeco(String hint, {required BookingFormDensity dens}) {
    return InputDecoration(
      hintText: hint.isEmpty ? null : hint,
      hintStyle: TextStyle(
        fontSize: dens.inputFont,
        fontWeight: FontWeight.w500,
        color: const Color(0xFF9DAAA3),
        height: 1.2,
      ),
      isDense: true,
      filled: true,
      fillColor: Colors.transparent,
      border: InputBorder.none,
      enabledBorder: InputBorder.none,
      focusedBorder: InputBorder.none,
      errorBorder: InputBorder.none,
      disabledBorder: InputBorder.none,
      contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
    );
  }

  /// Website `.booking-input` shell — fixed height, 1.5px `#dbe8df`, 8px radius.
  Widget _boxedShell({
    required double height,
    required Widget child,
    bool error = false,
  }) {
    return Container(
      height: height,
      width: double.infinity,
      alignment: Alignment.centerLeft,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: error ? Colors.red.shade400 : _line,
          width: 1.5,
        ),
      ),
      child: child,
    );
  }

  Widget _boxedInput({
    required double height,
    required Widget child,
    bool error = false,
  }) {
    return _boxedShell(height: height, error: error, child: child);
  }

  /// Website `.booking-phone-field` — compact prefix so 10 digits stay visible.
  Widget _phoneField({
    required BookingFormDensity dens,
    required double height,
    required ValueChanged<String> onChanged,
    bool error = false,
  }) {
    final digitSize = math.max(dens.inputFont, 13).toDouble();
    return _boxedShell(
      height: height,
      error: error,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _PhonePrefix(),
          Expanded(
            child: TextField(
              controller: _mobileCtrl,
              onChanged: onChanged,
              keyboardType: TextInputType.phone,
              textAlignVertical: TextAlignVertical.center,
              maxLines: 1,
              scrollPhysics: const ClampingScrollPhysics(),
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(10),
              ],
              style: TextStyle(
                fontSize: digitSize,
                fontWeight: FontWeight.w700,
                height: 1.15,
                letterSpacing: 0,
                fontFeatures: const [FontFeature.tabularFigures()],
                color: const Color(0xFF1B2A22),
              ),
              decoration: _borderlessDeco('10 digits', dens: dens).copyWith(
                contentPadding: const EdgeInsets.symmetric(horizontal: 6),
                isCollapsed: false,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Fixed-height tap field so Preferred Date/Time share identical box height.
  Widget _scheduleTapField({
    required BookingFormDensity dens,
    required double height,
    required VoidCallback onTap,
    required Widget child,
    Widget? prefix,
  }) {
    return SizedBox(
      height: height,
      width: double.infinity,
      child: Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: _line, width: 1.5),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Row(
              children: [
                if (prefix != null) ...[
                  prefix,
                  const SizedBox(width: 6),
                ],
                Expanded(
                  // Scale one line down so "Tomorrow • 27 Sep" stays inside
                  // the box on a 320px-wide phone instead of wrapping over Name.
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: child,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _label(String text, BookingFormDensity dens) => SizedBox(
        height: dens.labelBlock,
        child: Align(
          alignment: Alignment.topLeft,
          child: Text(
            text.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: dens.labelSize,
              fontWeight: FontWeight.w800,
              color: const Color(0xFF4B6255),
              letterSpacing: 0.02 * dens.labelSize,
              height: 1.1,
            ),
          ),
        ),
      );

  Widget _fieldError(String text) => Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Text(text, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.red)),
      );

  Widget _banner(String text, Color bg, Color fg) => SizedBox(
        height: BookingFormDensity.bannerH,
        child: Container(
          alignment: Alignment.centerLeft,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            text,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 11, height: 1.05, fontWeight: FontWeight.w700, color: fg),
          ),
        ),
      );
}

/// Fixed-size India flag so the emoji width does not steal digit space.
class _PhonePrefix extends StatelessWidget {
  const _PhonePrefix();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6),
      decoration: const BoxDecoration(
        color: Color(0xFFF4FAF6),
        border: Border(right: BorderSide(color: Color(0xFFDBE8DF), width: 1.5)),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _IndiaFlag(),
          SizedBox(width: 4),
          Text(
            '+91',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              height: 1,
              color: Color(0xFF1B2A22),
            ),
          ),
        ],
      ),
    );
  }
}

class _IndiaFlag extends StatelessWidget {
  const _IndiaFlag();

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      width: 16,
      height: 11,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.all(Radius.circular(1)),
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFFF9933),
              Color(0xFFFF9933),
              Color(0xFFFFFFFF),
              Color(0xFFFFFFFF),
              Color(0xFF138808),
              Color(0xFF138808),
            ],
            stops: [0, 0.33, 0.33, 0.66, 0.66, 1],
          ),
        ),
      ),
    );
  }
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
