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
import '../widgets/clock_time_picker.dart';
import '../widgets/website_booking_form.dart';
import '../core/booking_timezone.dart';
import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';
import '../providers/booking_flow_provider.dart';
import '../services/customer_services.dart';
import '../shared/widgets/pc99_widgets.dart';
import '../shared/widgets/service_guidelines_card.dart';
/// Website homepage booking form (Book Your Service).
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
  static const _green = Color(0xFF078B4F);
  static const _navy = Color(0xFF102E68);
  static const _line = Color(0xFFE4E9F0);

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
    final picked = await showClockTimePicker(
      context,
      hour24: parts.$1,
      minute: parts.$2,
    );
    if (picked != null) {
      flow.setPreferredTime(picked.$1, picked.$2);
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

    final profile = context.read<AuthProvider>().profile;
    final profileMobile = (profile?.mobile ?? '').replaceAll(RegExp(r'\D'), '');
    final flowMobile = flow.mobile.replaceAll(RegExp(r'\D'), '');
    if (context.read<AuthProvider>().loggedIn &&
        profileMobile.length == 10 &&
        profileMobile == flowMobile) {
      await _createLoggedInBooking(flow);
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

  Future<void> _createLoggedInBooking(BookingFlowProvider flow) async {
    setState(() {
      _busy = true;
      _submitMessage = null;
    });
    try {
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
      final booking = await BookingService(context.read<ApiClient>()).book(
        serviceType: q.serviceTypeLabel,
        pricingRateId: q.pricingRateId ?? 0,
        pricingRateIds: q.pricingRateIds,
        packageTier: q.packageTier,
        address: flow.streetAddress.trim(),
        fullAddress: flow.serviceFullAddress.isNotEmpty
            ? flow.serviceFullAddress
            : flow.streetAddress.trim(),
        city: flow.serviceCity.trim().isNotEmpty
            ? flow.serviceCity.trim()
            : _guessCity(flow.streetAddress),
        area: flow.serviceArea,
        bhkSize: flow.bhkSizeForApi,
        propertyType: flow.propertyTypeForApi,
        bookingType: flow.bookingTypeForApi,
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
      context.go('/book/confirmed');
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitMessage = _customerMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
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
        pricingRateIds: q.pricingRateIds,
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

  double _keyboardInset(BuildContext context) {
    final view = View.of(context);
    final fromView = view.viewInsets.bottom / view.devicePixelRatio;
    final fromMedia = MediaQuery.viewInsetsOf(context).bottom;
    return fromView > fromMedia ? fromView : fromMedia;
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

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();

    // Keep name/mobile in sync when the provider is prefilled.
    // Address sync is owned by BookingAddressField.
    if (_nameCtrl.text != flow.fullName && !_nameCtrl.selection.isValid) {
      _nameCtrl.text = flow.fullName;
    }
    if (_mobileCtrl.text != flow.mobile && !_mobileCtrl.selection.isValid) {
      _mobileCtrl.text = flow.mobile;
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F5),
      // The form scrolls itself. Letting the scaffold shrink the body made
      // FittedBox scale the whole booking card down when the keyboard opened.
      resizeToAvoidBottomInset: false,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _buildHeader(
              context,
              height: widget.embeddedInShell ? 48 : 52,
            ),
            Expanded(
              child: WebsiteStyleBookingForm(
                flow: flow,
                nameCtrl: _nameCtrl,
                mobileCtrl: _mobileCtrl,
                addressCtrl: _addressCtrl,
                errors: _errors,
                ratesError: flow.ratesError,
                submitMessage: _submitMessage,
                busy: _busy || _otpSending,
                onConfirm: _onConfirm,
                onPickDate: _pickDate,
                onPickTime: _pickTime,
                onTreatmentInfo: _showTreatmentInfo,
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
          18 + _keyboardInset(context),
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

  Widget _fieldError(String text) => Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Text(text, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.red)),
      );
}

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
