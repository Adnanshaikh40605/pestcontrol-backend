import 'dart:math' as math;

/// Which booking sections are on screen. Heights in [BookingFormDensity]
/// are solved against this shape so hiding treatment/plan does not leave a void.
class BookingFormShape {
  const BookingFormShape({
    this.showTreatment = true,
    this.showPlan = true,
    this.planTaller = false,
    this.banners = 0,
  });

  final bool showTreatment;
  final bool showPlan;

  /// Bed-bug plan copy needs a slightly taller card.
  final bool planTaller;

  /// Error / rates banners between the title and the property toggle.
  final int banners;

  /// `SizedBox(height: gap)` widgets between stacked blocks, including banners.
  int get sectionGapCount {
    var blocks = 6; // title, property, service, address, schedule, name
    if (showTreatment) blocks++;
    if (showPlan) blocks++;
    return (blocks - 1) + banners;
  }
}

/// Continuous spacing scale for the one-viewport home booking form.
///
/// Vertical sizes are solved from the [LayoutBuilder] body height (the area
/// under the logo header and above the shell bottom nav) so leftover height
/// becomes field height and section gaps instead of a single empty hole.
class BookingFormDensity {
  const BookingFormDensity({
    required this.gap,
    required this.ctaGap,
    required this.colGap,
    required this.inputH,
    required this.selectH,
    required this.choiceH,
    required this.propH,
    required this.priceH,
    required this.ctaH,
    required this.formPadH,
    required this.formPadV,
    required this.cardBottom,
    required this.titleSize,
    required this.warrantySize,
    required this.labelSize,
    required this.inputFont,
    required this.selectFont,
    required this.choiceTitle,
    required this.choiceSub,
    required this.ctaFont,
    required this.showTrust,
    required this.heroPadV,
    required this.heroTitle,
  });

  /// OTP sheet only — not viewport-fitted.
  static const sheet = BookingFormDensity(
    gap: 8,
    ctaGap: 6,
    colGap: 8,
    inputH: 42,
    selectH: 38,
    choiceH: 38,
    propH: 28,
    priceH: 36,
    ctaH: 42,
    formPadH: 10,
    formPadV: 8,
    cardBottom: 2,
    titleSize: 15,
    warrantySize: 10,
    labelSize: 9,
    inputFont: 14,
    selectFont: 11,
    choiceTitle: 11,
    choiceSub: 8,
    ctaFont: 14,
    showTrust: true,
    heroPadV: 8,
    heroTitle: 18,
  );

  static const badgeH = 14.0;
  static const afterBadge = 4.0;
  static const trustGap = 3.0;
  static const trustH = 12.0;
  static const bannerH = 26.0;

  final double gap;
  final double ctaGap;
  final double colGap;
  final double inputH;
  final double selectH;
  final double choiceH;
  final double propH;
  final double priceH;
  final double ctaH;
  final double formPadH;
  final double formPadV;
  final double cardBottom;
  final double titleSize;
  final double warrantySize;
  final double labelSize;
  final double inputFont;
  final double selectFont;
  final double choiceTitle;
  final double choiceSub;
  final double ctaFont;
  final bool showTrust;
  final double heroPadV;
  final double heroTitle;

  double get titleLine => titleSize * 1.15;

  /// Label text (`height: 1.1`) plus 2px before the control.
  double get labelBlock => labelSize * 1.1 + 2;

  double get propBlock => propH + 4;

  double get heroHeight {
    var h = heroPadV * 2 + badgeH + afterBadge + heroTitle * 1.05;
    if (showTrust) h += trustGap + trustH;
    return h;
  }

  double planHeight(BookingFormShape shape) =>
      choiceH + (shape.planTaller ? 6 : 0);

  /// Body height consumed by hero + card + the padding under the card.
  /// Must stay in lockstep with the home booking column.
  double occupied(BookingFormShape shape, {required double bottomPad}) {
    final label = labelBlock;
    var inner = titleLine;
    inner += shape.banners * (gap + bannerH);
    inner += gap + propBlock;
    inner += gap + label + selectH;
    if (shape.showTreatment) inner += gap + label + choiceH;
    if (shape.showPlan) inner += gap + label + planHeight(shape);
    inner += gap + label + inputH; // address
    inner += gap + label + inputH; // date / time
    inner += gap + label + inputH; // name / mobile
    inner += ctaGap + priceH + ctaGap + ctaH;
    return bottomPad + heroHeight + formPadV + inner + cardBottom;
  }

  /// Chrome-device body under the logo, above the shell nav.
  /// [safeTop] is consumed by SafeArea; [safeBottom] is added to the nav bar.
  static double bodyHeightForViewport({
    required double viewportHeight,
    double safeTop = 0,
    double safeBottom = 0,
    double headerHeight = 48,
    double navigationBarHeight = 48,
  }) {
    return viewportHeight -
        safeTop -
        headerHeight -
        navigationBarHeight -
        safeBottom;
  }

  /// Scale density so the resting form fills [bodyHeight].
  ///
  /// Below the compact floor the form keeps minimum sizes and the page scrolls.
  /// Above the comfortable scale, leftover pixels go into controls, then gaps,
  /// then card padding — never a single spacer between name and the price bar.
  static BookingFormDensity fit({
    required double bodyHeight,
    required double contentWidth,
    required BookingFormShape shape,
    required double bottomPad,
  }) {
    BookingFormDensity at(double t) =>
        BookingFormDensity._scaled(t, contentWidth);

    final floor = at(0);
    final floorH = floor.occupied(shape, bottomPad: bottomPad);
    if (floorH >= bodyHeight - 0.5) return floor;

    final comfort = at(1);
    final comfortH = comfort.occupied(shape, bottomPad: bottomPad);
    if (comfortH >= bodyHeight) {
      var lo = 0.0;
      var hi = 1.0;
      for (var i = 0; i < 24; i++) {
        final mid = (lo + hi) / 2;
        if (at(mid).occupied(shape, bottomPad: bottomPad) <= bodyHeight) {
          lo = mid;
        } else {
          hi = mid;
        }
      }
      return at(lo)._nudgeGap(bodyHeight, shape, bottomPad);
    }
    return comfort._growTo(bodyHeight, shape, bottomPad);
  }

  static BookingFormDensity _scaled(double t, double contentWidth) {
    final s = t.clamp(0.0, 1.0);
    double l(double a, double b) => a + (b - a) * s;
    // ~320px content (Galaxy S8+) cannot fit title + warranty at 15px.
    final narrow = contentWidth < 340;
    return BookingFormDensity(
      gap: l(6, 11),
      ctaGap: l(5, 8),
      colGap: l(6, 10),
      inputH: l(36, 44),
      selectH: l(36, 42),
      choiceH: l(38, 48),
      propH: l(28, 34),
      priceH: l(34, 40),
      ctaH: l(42, 48),
      formPadH: 10,
      formPadV: l(6, 10),
      cardBottom: 2,
      titleSize: narrow ? 13.5 : l(15, 16),
      warrantySize: narrow ? 9 : l(10, 10.5),
      labelSize: l(8.5, 9.5),
      inputFont: l(12.5, 13.5),
      selectFont: 11.5,
      choiceTitle: 11,
      choiceSub: 8.5,
      ctaFont: l(14, 15),
      showTrust: true,
      heroPadV: l(5, 8),
      heroTitle: narrow ? l(16, 17.5) : l(17, 19),
    );
  }

  BookingFormDensity _nudgeGap(
    double bodyHeight,
    BookingFormShape shape,
    double bottomPad,
  ) {
    final slots = shape.sectionGapCount;
    if (slots <= 0) return this;
    final left = bodyHeight - occupied(shape, bottomPad: bottomPad);
    if (left.abs() < 0.05) return this;
    return _copy(gap: gap + left / slots);
  }

  /// Push surplus body height into controls first, then section gaps, then
  /// the card's vertical padding so the page still fills.
  BookingFormDensity _growTo(
    double bodyHeight,
    BookingFormShape shape,
    double bottomPad,
  ) {
    var gap = this.gap;
    var ctaGap = this.ctaGap;
    var inputH = this.inputH;
    var selectH = this.selectH;
    var choiceH = this.choiceH;
    var propH = this.propH;
    var priceH = this.priceH;
    var ctaH = this.ctaH;
    var heroPadV = this.heroPadV;
    var heroTitle = this.heroTitle;
    var formPadV = this.formPadV;
    var cardBottom = this.cardBottom;

    BookingFormDensity snap() => _copy(
          gap: gap,
          ctaGap: ctaGap,
          inputH: inputH,
          selectH: selectH,
          choiceH: choiceH,
          propH: propH,
          priceH: priceH,
          ctaH: ctaH,
          heroPadV: heroPadV,
          heroTitle: heroTitle,
          formPadV: formPadV,
          cardBottom: cardBottom,
        );

    var left = bodyHeight - snap().occupied(shape, bottomPad: bottomPad);

    void take(double room, void Function(double used) apply) {
      if (left <= 0.05 || room <= 0.05) return;
      final used = math.min(left, room);
      apply(used);
      left = bodyHeight - snap().occupied(shape, bottomPad: bottomPad);
    }

    take((54 - inputH) * 3, (used) => inputH += used / 3);
    take(50 - selectH, (used) => selectH += used);
    final choiceUnits =
        (shape.showTreatment ? 1 : 0) + (shape.showPlan ? 1 : 0);
    if (choiceUnits > 0) {
      take(
        (62 - choiceH) * choiceUnits,
        (used) => choiceH += used / choiceUnits,
      );
    }
    take(40 - propH, (used) => propH += used);
    take(46 - priceH, (used) => priceH += used);
    take(52 - ctaH, (used) => ctaH += used);
    take((12 - heroPadV) * 2, (used) => heroPadV += used / 2);
    take((22 - heroTitle) * 1.05, (used) => heroTitle += used / 1.05);
    take(14 - formPadV, (used) => formPadV += used);

    final slots = shape.sectionGapCount.toDouble();
    if (slots > 0) {
      take((16 - gap) * slots, (used) => gap += used / slots);
    }
    take((10 - ctaGap) * 2, (used) => ctaGap += used / 2);

    if (left > 0.05 && slots > 0) {
      final room = math.max(0.0, 22 - gap) * slots;
      final used = math.min(left, room);
      if (used > 0) {
        gap += used / slots;
        left = bodyHeight - snap().occupied(shape, bottomPad: bottomPad);
      }
    }
    if (left > 0.05) {
      formPadV += left / 2;
      cardBottom += left / 2;
      left = bodyHeight - snap().occupied(shape, bottomPad: bottomPad);
    }
    if (left.abs() > 0.05 && slots > 0) {
      gap += left / slots;
    }
    return snap();
  }

  BookingFormDensity _copy({
    double? gap,
    double? ctaGap,
    double? colGap,
    double? inputH,
    double? selectH,
    double? choiceH,
    double? propH,
    double? priceH,
    double? ctaH,
    double? formPadV,
    double? cardBottom,
    double? heroPadV,
    double? heroTitle,
  }) {
    return BookingFormDensity(
      gap: gap ?? this.gap,
      ctaGap: ctaGap ?? this.ctaGap,
      colGap: colGap ?? this.colGap,
      inputH: inputH ?? this.inputH,
      selectH: selectH ?? this.selectH,
      choiceH: choiceH ?? this.choiceH,
      propH: propH ?? this.propH,
      priceH: priceH ?? this.priceH,
      ctaH: ctaH ?? this.ctaH,
      formPadH: formPadH,
      formPadV: formPadV ?? this.formPadV,
      cardBottom: cardBottom ?? this.cardBottom,
      titleSize: titleSize,
      warrantySize: warrantySize,
      labelSize: labelSize,
      inputFont: inputFont,
      selectFont: selectFont,
      choiceTitle: choiceTitle,
      choiceSub: choiceSub,
      ctaFont: ctaFont,
      showTrust: showTrust,
      heroPadV: heroPadV ?? this.heroPadV,
      heroTitle: heroTitle ?? this.heroTitle,
    );
  }
}
