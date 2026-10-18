import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../providers/booking_flow_provider.dart';
import '../utils/catalog_pricing.dart';
import 'booking_address_field.dart';

/// Homepage booking form from the PestControl99 website, in the customer app.
class WebsiteStyleBookingForm extends StatefulWidget {
  const WebsiteStyleBookingForm({
    super.key,
    required this.flow,
    required this.nameCtrl,
    required this.mobileCtrl,
    required this.addressCtrl,
    required this.errors,
    required this.ratesError,
    required this.submitMessage,
    required this.busy,
    required this.onConfirm,
    required this.onPickDate,
    required this.onPickTime,
    required this.onTreatmentInfo,
  });

  final BookingFlowProvider flow;
  final TextEditingController nameCtrl;
  final TextEditingController mobileCtrl;
  final TextEditingController addressCtrl;
  final Map<String, String> errors;
  final String? ratesError;
  final String? submitMessage;
  final bool busy;
  final VoidCallback onConfirm;
  final VoidCallback onPickDate;
  final VoidCallback onPickTime;
  final ValueChanged<String> onTreatmentInfo;

  @override
  State<WebsiteStyleBookingForm> createState() => _WebsiteStyleBookingFormState();
}

class _WebsiteStyleBookingFormState extends State<WebsiteStyleBookingForm> {
  static const _green = Color(0xFF078B4F);
  static const _soft = Color(0xFFEEF9F3);
  static const _navy = Color(0xFF102E68);
  static const _line = Color(0xFFE4E9F0);
  static const _blue = Color(0xFF1D6FD6);
  static const _orange = Color(0xFFE06A13);
  static const _deepUrl = 'https://www.deepcleaning99.com/';

  static const _pests = <({String value, String label, String asset})>[
    (value: 'cockroach-ants', label: 'Cockroach & Ants', asset: 'assets/images/booking-pests/cockroach.jpg'),
    (value: 'bedbugs', label: 'Bed Bugs', asset: 'assets/images/booking-pests/bedbug.jpg'),
    (value: 'termite', label: 'Termite', asset: 'assets/images/booking-pests/termite.jpg'),
    (value: 'rodent', label: 'Rodent', asset: 'assets/images/booking-pests/rodent.jpg'),
    (value: 'mosquito', label: 'Mosquito', asset: 'assets/images/booking-pests/mosquito.jpg'),
    (value: 'wood-borer', label: 'Wood Borer', asset: 'assets/images/booking-pests/woodborer.jpg'),
  ];

  static const _sizes = <({String value, String label})>[
    (value: '1rk', label: '1RK'),
    (value: '1bhk', label: '1BHK'),
    (value: '2bhk', label: '2BHK'),
    (value: '3bhk', label: '3BHK'),
    (value: '4bhk', label: '4BHK'),
  ];

  static const _deepChips = [
    'Full Home',
    'Kitchen',
    'Sofa',
    'Bathroom',
    'Mattress',
    'Carpet',
    'Office',
  ];

  /// Flat / Villa is display-only. Both use the same home-size catalog rate.
  String _homeKind = 'flat';

  BookingFlowProvider get flow => widget.flow;

  Future<void> _openDeepCleaning() async {
    final uri = Uri.parse(_deepUrl);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final q = flow.quote;
    final residential = !flow.isInspectionQuote;

    final card = Container(
        padding: const EdgeInsets.fromLTRB(10, 4, 10, 4),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: _line),
          boxShadow: const [
            BoxShadow(color: Color(0x14102E68), blurRadius: 18, offset: Offset(0, 6)),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Book Your Service',
              style: TextStyle(fontSize: 16.5, fontWeight: FontWeight.w800, color: _navy, height: 1.1),
            ),
            if (widget.ratesError != null) ...[
              const SizedBox(height: 8),
              _Note(widget.ratesError!, const Color(0xFFFFF8E8), const Color(0xFF8A5A00)),
            ],
            if (widget.submitMessage != null) ...[
              const SizedBox(height: 8),
              _Note(widget.submitMessage!, const Color(0xFFFFF1F1), const Color(0xFFB42318)),
            ],
            const SizedBox(height: 4),
            _pair(
              left: _PairButton(
                label: 'Residential',
                selected: flow.premiseType == 'residential',
                icon: Icons.home_outlined,
                onTap: () => flow.setPremiseType('residential'),
              ),
              right: _PairButton(
                label: 'Commercial',
                selected: flow.premiseType == 'commercial',
                icon: Icons.apartment_outlined,
                onTap: () => flow.setPremiseType('commercial'),
              ),
            ),
            const _FieldLabel('What pest problem?', required: true),
            _pestGrid(),
            if (widget.errors['pestTypes'] != null) _ErrorText(widget.errors['pestTypes']!),
            const _FieldLabel('Property type'),
            _pair(
              left: _PairButton(
                label: 'Flat',
                selected: _homeKind == 'flat',
                icon: Icons.apartment_outlined,
                onTap: () => setState(() => _homeKind = 'flat'),
              ),
              right: _PairButton(
                label: 'Villa',
                selected: _homeKind == 'villa',
                icon: Icons.home_work_outlined,
                onTap: () => setState(() => _homeKind = 'villa'),
              ),
            ),
            const _FieldLabel('Home size'),
            _sizeChips(enabled: residential),
            if (widget.errors['premiseSize'] != null) _ErrorText(widget.errors['premiseSize']!),
            if (residential && flow.showTreatmentQuality) ...[
              const _FieldLabel('Choose treatment', required: true),
              Row(
                children: [
                  Expanded(child: _treatmentCard('standard', 'Standard', 'Spray + standard gel', 'Kitchen items need removal')),
                  const SizedBox(width: 8),
                  Expanded(child: _treatmentCard('premium', 'Premium', 'Odourless gel', 'No kitchen item removal')),
                ],
              ),
              if (widget.errors['treatmentQuality'] != null) _ErrorText(widget.errors['treatmentQuality']!),
            ],
            if (residential) ...[
              const _FieldLabel('Service plan', required: true),
              _pair(
                left: _PlanButton(
                  title: flow.oneTimePlanTitle,
                  sub: flow.oneTimePlanSub,
                  selected: flow.serviceType == 'one-time',
                  icon: Icons.calendar_today_outlined,
                  onTap: () => flow.setServiceType('one-time'),
                ),
                right: _PlanButton(
                  title: 'AMC',
                  sub: flow.amcAvailable ? 'Annual plan' : BookingFlowProvider.amcUnavailableLabel,
                  selected: flow.serviceType == 'amc',
                  enabled: flow.amcAvailable,
                  badge: flow.amcAvailable ? null : BookingFlowProvider.amcUnavailableBadge,
                  icon: Icons.autorenew,
                  onTap: () => flow.setServiceType('amc'),
                ),
              ),
              if (widget.errors['serviceType'] != null) _ErrorText(widget.errors['serviceType']!),
            ],
            const SizedBox(height: 4),
            BookingAddressField(
              controller: widget.addressCtrl,
              height: 32,
              scrollPadding: EdgeInsets.only(bottom: _keyboardInset(context) + 32, top: 72),
              errorText: widget.errors['streetAddress'],
              errorBorder: widget.errors['streetAddress'] != null,
              decoration: const InputDecoration(
                isDense: true,
                border: InputBorder.none,
                hintText: 'Area, building & full address',
                hintStyle: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF8B95A6)),
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: _IconField(
                    icon: Icons.calendar_today_outlined,
                    text: flow.friendlyPreferredDate.isEmpty ? 'Select date' : flow.friendlyPreferredDate,
                    placeholder: flow.friendlyPreferredDate.isEmpty,
                    error: widget.errors['preferredDate'] != null,
                    onTap: widget.onPickDate,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _IconField(
                    icon: Icons.schedule_outlined,
                    text: flow.preferredTime.isEmpty ? 'Select time' : flow.timeSlotLabel,
                    placeholder: flow.preferredTime.isEmpty,
                    error: widget.errors['preferredTime'] != null,
                    onTap: widget.onPickTime,
                  ),
                ),
              ],
            ),
            if (widget.errors['preferredDate'] != null || widget.errors['preferredTime'] != null)
              _ErrorText(widget.errors['preferredDate'] ?? widget.errors['preferredTime']!),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(child: _nameField()),
                const SizedBox(width: 8),
                Expanded(child: _phoneField()),
              ],
            ),
            if (widget.errors['name'] != null || widget.errors['phone'] != null)
              _ErrorText(widget.errors['name'] ?? widget.errors['phone']!),
            const SizedBox(height: 4),
            _priceBar(q),
            const SizedBox(height: 4),
            SizedBox(
              height: 32,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: _green,
                  disabledBackgroundColor: _green.withValues(alpha: 0.7),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
                  elevation: 0,
                ),
                onPressed: widget.busy ? null : widget.onConfirm,
                child: Text(
                  widget.busy
                      ? 'Sending OTP…'
                      : flow.isOtherPremiseSize
                          ? 'Call / WhatsApp for Quote →'
                          : 'Confirm Booking →',
                  style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w800, color: Colors.white),
                ),
              ),
            ),
            const SizedBox(height: 4),
            _deepCleaning(),
          ],
        ),
      );

    final keyboard = _keyboardInset(context);
    // Always lay the form out at the screen width. FittedBox used to scale
    // the whole card down when the keyboard opened, and on web that scale
    // also tiled the form down the page.
    return SingleChildScrollView(
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: EdgeInsets.fromLTRB(4, 2, 4, 2 + keyboard),
      child: card,
    );
  }

  double _keyboardInset(BuildContext context) {
    final view = View.of(context);
    final fromView = view.viewInsets.bottom / view.devicePixelRatio;
    final fromMedia = MediaQuery.viewInsetsOf(context).bottom;
    return fromView > fromMedia ? fromView : fromMedia;
  }

  Widget _pair({required Widget left, required Widget right}) {
    return Row(
      children: [
        Expanded(child: left),
        const SizedBox(width: 8),
        Expanded(child: right),
      ],
    );
  }

  Widget _pestGrid() {
    return SizedBox(
      height: 88,
      child: Column(
        children: [
          for (var row = 0; row < 2; row++) ...[
            if (row > 0) const SizedBox(height: 4),
            Expanded(
              child: Row(
                children: [
                  for (var col = 0; col < 3; col++) ...[
                    if (col > 0) const SizedBox(width: 4),
                    Expanded(
                      child: _PestCard(
                        label: _pests[row * 3 + col].label,
                        asset: _pests[row * 3 + col].asset,
                        selected: flow.pestTypes.contains(_pests[row * 3 + col].value),
                        onTap: () => flow.togglePest(_pests[row * 3 + col].value),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _sizeChips({required bool enabled}) {
    return Row(
      children: [
        for (var i = 0; i < _sizes.length; i++) ...[
          if (i > 0) const SizedBox(width: 4),
          Expanded(
            child: _SizeChip(
              label: _sizes[i].label,
              selected: flow.premiseSize == _sizes[i].value,
              enabled: enabled,
              onTap: () => flow.setPremiseSize(_sizes[i].value),
            ),
          ),
        ],
      ],
    );
  }

  Widget _treatmentCard(String value, String title, String line1, String line2) {
    final selected = flow.treatmentQuality == value;
    return Material(
      color: selected ? _soft : Colors.white,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: () => flow.setTreatmentQuality(value),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.fromLTRB(6, 3, 6, 3),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: selected ? _green : _line, width: selected ? 1.5 : 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: _navy, height: 1)),
                  ),
                  if (selected) const _Tick(),
                ],
              ),
              _checkLine(line1),
              Row(
                children: [
                  Expanded(child: _checkLine(line2)),
                  GestureDetector(
                    onTap: () => widget.onTreatmentInfo(value),
                    child: const Padding(
                      padding: EdgeInsets.only(left: 4),
                      child: Text(
                        'Benefits',
                        style: TextStyle(color: _blue, fontSize: 11, fontWeight: FontWeight.w800),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _checkLine(String text) {
    return Row(
      children: [
        const Icon(Icons.check, size: 12, color: _green),
        const SizedBox(width: 3),
        Expanded(
          child: Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600, color: Color(0xFF3D4C63)),
          ),
        ),
      ],
    );
  }

  Widget _nameField() {
    return _FieldShell(
      error: widget.errors['name'] != null,
      child: TextField(
        controller: widget.nameCtrl,
        onChanged: (value) {
          flow.setFullName(value);
          if (widget.nameCtrl.text != flow.fullName) {
            widget.nameCtrl.value = TextEditingValue(
              text: flow.fullName,
              selection: TextSelection.collapsed(offset: flow.fullName.length),
            );
          }
        },
        keyboardType: TextInputType.name,
        textCapitalization: TextCapitalization.words,
        textAlignVertical: TextAlignVertical.center,
        scrollPadding: EdgeInsets.only(bottom: _keyboardInset(context) + 32, top: 72),
        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: _navy),
        inputFormatters: [
          FilteringTextInputFormatter.allow(RegExp(r'[\p{L}\s]', unicode: true)),
        ],
        decoration: const InputDecoration(
          isDense: true,
          border: InputBorder.none,
          prefixIcon: Icon(Icons.person_outline, size: 16, color: _green),
          prefixIconConstraints: BoxConstraints(minWidth: 28, minHeight: 28),
          hintText: 'Full name',
          hintStyle: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF8B95A6)),
          contentPadding: EdgeInsets.zero,
        ),
      ),
    );
  }

  Widget _phoneField() {
    return _FieldShell(
      error: widget.errors['phone'] != null,
      child: TextField(
        controller: widget.mobileCtrl,
        onChanged: flow.setMobile,
        keyboardType: TextInputType.phone,
        textAlignVertical: TextAlignVertical.center,
        scrollPadding: EdgeInsets.only(bottom: _keyboardInset(context) + 32, top: 72),
        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: _navy),
        inputFormatters: [
          FilteringTextInputFormatter.digitsOnly,
          LengthLimitingTextInputFormatter(10),
        ],
        decoration: const InputDecoration(
          isDense: true,
          border: InputBorder.none,
          prefixIcon: _PhonePrefix(),
          prefixIconConstraints: BoxConstraints(minWidth: 58, minHeight: 28),
          hintText: '10-digit number',
          hintStyle: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF8B95A6)),
          contentPadding: EdgeInsets.zero,
        ),
      ),
    );
  }

  Widget _priceBar(QuotePriceResult q) {
    final showPromo = flow.selectionsComplete &&
        !flow.isInspectionQuote &&
        !q.pricePending &&
        !flow.ratesLoading &&
        q.offerPrice > 0 &&
        q.listPrice > q.offerPrice &&
        q.discountPercent > 0;
    final showGst = flow.selectionsComplete &&
        !flow.isInspectionQuote &&
        !q.pricePending &&
        !flow.ratesLoading &&
        q.offerPrice > 0;

    Widget amount;
    if (flow.ratesLoading) {
      amount = const Text('…', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: _green));
    } else if (flow.isInspectionQuote) {
      amount = const Text('Free visit', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: _green));
    } else if (showPromo) {
      amount = Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            BookingFlowProvider.formatInr(q.listPrice),
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: Color(0xFF8B95A6),
              decoration: TextDecoration.lineThrough,
            ),
          ),
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
            decoration: BoxDecoration(color: _orange, borderRadius: BorderRadius.circular(999)),
            child: Text(
              '${q.discountPercent}% OFF',
              style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w800),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            BookingFlowProvider.formatInr(q.offerPrice),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: _green, height: 1),
          ),
        ],
      );
    } else if (flow.selectionsComplete && !q.pricePending && q.offerPrice > 0) {
      amount = Text(
        BookingFlowProvider.formatInr(q.offerPrice),
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: _green),
      );
    } else if (flow.selectionsComplete && (q.pricePending || flow.isOtherPremiseSize)) {
      amount = const Text('On request', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: _green));
    } else {
      amount = const Text('₹0', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: _green));
    }

    return Container(
      constraints: const BoxConstraints(minHeight: 44),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFE7F7EE),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFD7F0E2)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  flow.priceSummaryLabel,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF5D6B80)),
                ),
                if (showGst)
                  const Text(
                    'Price (Excluding GST)',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: _orange),
                  ),
              ],
            ),
          ),
          amount,
        ],
      ),
    );
  }

  Widget _deepCleaning() {
    return Container(
      padding: const EdgeInsets.fromLTRB(6, 4, 6, 4),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F7FC),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFD3E2F2)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              const Icon(Icons.home_outlined, size: 18, color: Color(0xFF1D4F91)),
              const SizedBox(width: 6),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Deep Cleaning Services',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: _navy, height: 1.1),
                    ),
                    GestureDetector(
                      onTap: _openDeepCleaning,
                      child: const Text(
                        'Deepcleaning99.com',
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: _blue),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          SizedBox(
            height: 22,
            width: 200,
            child: FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: _navy,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                padding: EdgeInsets.zero,
              ),
              onPressed: _openDeepCleaning,
              child: const Text(
                'Book Deep Cleaning ↗',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Colors.white),
              ),
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 4,
            runSpacing: 4,
            children: [
              for (final chip in _deepChips)
                GestureDetector(
                  onTap: _openDeepCleaning,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: const Color(0xFFD3E2F2)),
                    ),
                    child: Text(
                      chip,
                      style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: _navy),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PestCard extends StatelessWidget {
  const _PestCard({
    required this.label,
    required this.asset,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String asset;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final background = selected ? const Color(0xFFEEF9F3) : Colors.white;
    return Material(
      color: background,
      borderRadius: BorderRadius.circular(9),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(9),
        child: Container(
          padding: const EdgeInsets.fromLTRB(2, 1, 2, 2),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: selected ? const Color(0xFF078B4F) : const Color(0xFFE4E9F0),
              width: selected ? 1.5 : 1,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: Stack(
            fit: StackFit.expand,
            children: [
              Column(
                children: [
                  Expanded(
                    child: ColoredBox(
                      color: background,
                      child: _PestPhoto(asset: asset),
                    ),
                  ),
                  ColoredBox(
                    color: background,
                    child: SizedBox(
                      width: double.infinity,
                      child: Text(
                        label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF102E68),
                          height: 1.1,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              if (selected) const Positioned(top: 1, right: 1, child: _Tick(size: 13)),
            ],
          ),
        ),
      ),
    );
  }
}

/// Full insect, centred, with the white photo background blended into the
/// card — the same treatment as the website pest cards.
class _PestPhoto extends StatefulWidget {
  const _PestPhoto({required this.asset});

  final String asset;

  @override
  State<_PestPhoto> createState() => _PestPhotoState();
}

class _PestPhotoState extends State<_PestPhoto> {
  ImageStream? _stream;
  ImageInfo? _info;
  late final ImageStreamListener _listener = ImageStreamListener(
    (info, _) {
      if (!mounted) return;
      setState(() => _info = info);
    },
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _resolve();
  }

  @override
  void didUpdateWidget(covariant _PestPhoto oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.asset != widget.asset) _resolve();
  }

  void _resolve() {
    final stream = AssetImage(widget.asset).resolve(createLocalImageConfiguration(context));
    if (identical(stream, _stream)) return;
    _stream?.removeListener(_listener);
    _stream = stream;
    stream.addListener(_listener);
  }

  @override
  void dispose() {
    _stream?.removeListener(_listener);
    _info?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _PestPhotoPainter(_info?.image),
      child: const SizedBox.expand(),
    );
  }
}

class _PestPhotoPainter extends CustomPainter {
  _PestPhotoPainter(this.image);

  final ui.Image? image;

  @override
  void paint(Canvas canvas, Size size) {
    final image = this.image;
    if (image == null || size.isEmpty) return;
    paintImage(
      canvas: canvas,
      rect: Offset.zero & size,
      image: image,
      fit: BoxFit.contain,
      alignment: Alignment.center,
      blendMode: BlendMode.multiply,
      filterQuality: FilterQuality.medium,
    );
  }

  @override
  bool shouldRepaint(covariant _PestPhotoPainter oldDelegate) => oldDelegate.image != image;
}

class _PairButton extends StatelessWidget {
  const _PairButton({
    required this.label,
    required this.selected,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? const Color(0xFFEEF9F3) : Colors.white,
      borderRadius: BorderRadius.circular(9),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(9),
        child: Container(
          height: 32,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: selected ? const Color(0xFF078B4F) : const Color(0xFFE4E9F0),
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Row(
            children: [
              Icon(icon, size: 16, color: selected ? const Color(0xFF078B4F) : const Color(0xFF5D6B80)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w800,
                    color: selected ? const Color(0xFF078B4F) : const Color(0xFF102E68),
                  ),
                ),
              ),
              if (selected) const _Tick(),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlanButton extends StatelessWidget {
  const _PlanButton({
    required this.title,
    required this.sub,
    required this.selected,
    required this.icon,
    required this.onTap,
    this.enabled = true,
    this.badge,
  });

  final String title;
  final String sub;
  final bool selected;
  final bool enabled;
  final String? badge;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fg = enabled ? const Color(0xFF102E68) : const Color(0xFF8B95A6);
    return Material(
      color: selected ? const Color(0xFFEEF9F3) : Colors.white,
      borderRadius: BorderRadius.circular(9),
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(9),
        child: Container(
          constraints: const BoxConstraints(minHeight: 32),
          padding: const EdgeInsets.fromLTRB(6, 3, 4, 3),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: selected ? const Color(0xFF078B4F) : const Color(0xFFE4E9F0),
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Stack(
            children: [
              Row(
                children: [
                  Icon(icon, size: 16, color: enabled ? const Color(0xFF078B4F) : const Color(0xFF8B95A6)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: fg)),
                        Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600, color: Color(0xFF5D6B80), height: 1.15)),
                      ],
                    ),
                  ),
                  if (selected) const _Tick(),
                ],
              ),
              if (badge != null)
                Positioned(
                  right: 0,
                  top: 0,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                    decoration: BoxDecoration(color: const Color(0xFF6C7F74), borderRadius: BorderRadius.circular(4)),
                    child: Text(badge!, style: const TextStyle(color: Colors.white, fontSize: 7, fontWeight: FontWeight.w800)),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SizeChip extends StatelessWidget {
  const _SizeChip({
    required this.label,
    required this.selected,
    required this.enabled,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? const Color(0xFFEEF9F3) : Colors.white,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          height: 32,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: selected ? const Color(0xFF078B4F) : const Color(0xFFE4E9F0),
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: enabled
                      ? (selected ? const Color(0xFF078B4F) : const Color(0xFF102E68))
                      : const Color(0xFFB0B8C4),
                ),
              ),
              if (selected) ...[const SizedBox(width: 4), const _Tick(size: 12)],
            ],
          ),
        ),
      ),
    );
  }
}

class _IconField extends StatelessWidget {
  const _IconField({
    required this.icon,
    required this.text,
    required this.placeholder,
    required this.error,
    required this.onTap,
  });

  final IconData icon;
  final String text;
  final bool placeholder;
  final bool error;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(9),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(9),
        child: Container(
          height: 32,
          padding: const EdgeInsets.symmetric(horizontal: 6),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(9),
            border: Border.all(color: error ? const Color(0xFFE23B3B) : const Color(0xFFE4E9F0)),
          ),
          child: Row(
            children: [
              Icon(icon, size: 15, color: const Color(0xFF078B4F)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  text,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: placeholder ? const Color(0xFF8B95A6) : const Color(0xFF102E68),
                  ),
                ),
              ),
              const Icon(Icons.expand_more, size: 16, color: Color(0xFF8B95A6)),
            ],
          ),
        ),
      ),
    );
  }
}

class _FieldShell extends StatelessWidget {
  const _FieldShell({required this.child, required this.error});

  final Widget child;
  final bool error;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 32,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: error ? const Color(0xFFE23B3B) : const Color(0xFFE4E9F0)),
      ),
      child: child,
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text, {this.required = false});

  final String text;
  final bool required;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 3, bottom: 2),
      child: Text.rich(
        TextSpan(
          text: text,
          children: [
            if (required)
              const TextSpan(text: ' *', style: TextStyle(color: Color(0xFFE23B3B))),
          ],
        ),
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF102E68), height: 1),
      ),
    );
  }
}

class _Tick extends StatelessWidget {
  const _Tick({this.size = 14});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(color: Color(0xFF078B4F), shape: BoxShape.circle),
      child: Icon(Icons.check, size: size - 4, color: Colors.white),
    );
  }
}

class _ErrorText extends StatelessWidget {
  const _ErrorText(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Text(text, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFFE23B3B))),
    );
  }
}

class _Note extends StatelessWidget {
  const _Note(this.text, this.bg, this.fg);

  final String text;
  final Color bg;
  final Color fg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(8)),
      child: Text(text, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: fg)),
    );
  }
}

class _PhonePrefix extends StatelessWidget {
  const _PhonePrefix();

  @override
  Widget build(BuildContext context) {
    return const Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(width: 8),
        _IndiaFlag(),
        SizedBox(width: 4),
        Text('+91', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF102E68))),
      ],
    );
  }
}

class _IndiaFlag extends StatelessWidget {
  const _IndiaFlag();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 16,
      height: 11,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(1),
        border: Border.all(color: const Color(0xFFE5E8EE)),
      ),
      child: Column(
        children: const [
          Expanded(child: ColoredBox(color: Color(0xFFFF9933))),
          Expanded(child: ColoredBox(color: Colors.white)),
          Expanded(child: ColoredBox(color: Color(0xFF138808))),
        ],
      ),
    );
  }
}
