import 'money_format.dart';

/// Customer payable split for Cash / Online collection UI.
///
/// Job amounts from the API are GST-inclusive. Prefer server fields when present;
/// otherwise derive from the inclusive total at [defaultGstPercent].
class GstBreakdown {
  const GstBreakdown({
    required this.baseAmount,
    required this.gstAmount,
    required this.totalAmount,
    required this.gstPercent,
  });

  final String baseAmount;
  final String gstAmount;
  final String totalAmount;
  final String gstPercent;

  static const double defaultGstPercent = 18;

  /// Prefer API fields; fall back to deriving from [inclusiveTotal].
  factory GstBreakdown.resolve({
    String? baseAmount,
    String? gstAmount,
    String? totalAmount,
    String? gstPercent,
    String? inclusiveTotal,
  }) {
    final total = _pickAmount(totalAmount) ?? _pickAmount(inclusiveTotal);
    final base = _pickAmount(baseAmount);
    final gst = _pickAmount(gstAmount);
    final pctRaw = (gstPercent ?? '').trim();
    final pct = double.tryParse(pctRaw.replaceAll('%', '')) ?? defaultGstPercent;

    if (base != null && gst != null && total != null) {
      return GstBreakdown(
        baseAmount: _fmt(base),
        gstAmount: _fmt(gst),
        totalAmount: _fmt(total),
        gstPercent: _fmtPct(pct),
      );
    }

    if (total != null && total > 0) {
      final rate = pct < 0 ? 0.0 : pct;
      final derivedBase = rate <= 0 ? total : total / (1 + rate / 100);
      final derivedGst = total - derivedBase;
      return GstBreakdown(
        baseAmount: _fmt(derivedBase),
        gstAmount: _fmt(derivedGst),
        totalAmount: _fmt(total),
        gstPercent: _fmtPct(rate),
      );
    }

    return GstBreakdown(
      baseAmount: '0',
      gstAmount: '0',
      totalAmount: '0',
      gstPercent: _fmtPct(pct),
    );
  }

  String get gstLabel {
    final clean = gstPercent.endsWith('.00')
        ? gstPercent.substring(0, gstPercent.length - 3)
        : gstPercent;
    return 'GST ($clean%)';
  }

  bool get hasAmount {
    final t = MoneyFormat.asDouble(totalAmount) ?? 0;
    return t > 0;
  }

  static double? _pickAmount(String? raw) => MoneyFormat.asDouble(raw);

  static String _fmt(double v) {
    if (v == v.roundToDouble()) return v.toStringAsFixed(0);
    return v.toStringAsFixed(2);
  }

  static String _fmtPct(double v) {
    if (v == v.roundToDouble()) return v.toStringAsFixed(0);
    return v.toStringAsFixed(2);
  }
}
