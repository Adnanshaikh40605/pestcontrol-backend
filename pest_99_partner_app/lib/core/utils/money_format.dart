/// Shared money formatting helpers for partner app payout UI.
class MoneyFormat {
  MoneyFormat._();

  static String rupees(String? raw) {
    if (raw == null) return '—';
    final t = raw.trim();
    if (t.isEmpty || t == 'null') return '—';
    if (t.startsWith('₹')) return t;
    // Included / free labels pass through.
    if (!RegExp(r'^-?\d').hasMatch(t)) return t;
    return '₹$t';
  }

  static double? asDouble(String? raw) {
    if (raw == null) return null;
    final cleaned = raw.replaceAll(RegExp(r'[^\d.\-]'), '');
    if (cleaned.isEmpty) return null;
    return double.tryParse(cleaned);
  }

  static String sumRupees(Iterable<String?> amounts) {
    var total = 0.0;
    var any = false;
    for (final a in amounts) {
      final v = asDouble(a);
      if (v == null) continue;
      total += v;
      any = true;
    }
    if (!any) return '₹0';
    if (total == total.roundToDouble()) {
      return '₹${total.toStringAsFixed(0)}';
    }
    return '₹${total.toStringAsFixed(2)}';
  }
}
