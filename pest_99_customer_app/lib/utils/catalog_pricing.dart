import '../models/customer_models.dart';

/// Website pest slug → keywords used against CRM service_package names.
const Map<String, List<String>> pestMatchKeys = {
  'cockroach-ants': ['cockroach', 'ant'],
  'mosquito': ['mosquito'],
  'termite': ['termite'],
  'rodent': ['rodent', 'rat'],
  'bedbugs': ['bed bug', 'bedbug', 'bed bugs'],
  'honey-bee': ['bee', 'wasp'],
  'wood-borer': ['wood borer', 'woodborer', 'borer'],
  'house-fly': ['house fly', 'housefly', 'fly control', 'flies', 'fly'],
  'hotel-commercial': ['general', 'commercial'],
  'other': ['general pest', 'general'],
};

/// Preferred CRM package names (ordered) for residential home booking.
const Map<String, Map<String, List<String>>> pestPreferredPackages = {
  'cockroach-ants': {
    'standard': ['Cockroach Standard', 'Cockroach / Ants'],
    'premium': ['Cockroach Premium', 'Cockroach Standard', 'Cockroach / Ants'],
  },
  'rodent': {
    'standard': ['Regular Rodent', 'Rodent'],
    'premium': ['Kill-Rodent System', 'Regular Rodent', 'Rodent'],
  },
  'mosquito': {
    'standard': ['Mosquito Cold Fogging', 'Mosquito'],
    'premium': ['Mosquito Thermal Fogging', 'Mosquito Cold Fogging', 'Mosquito'],
  },
  'termite': {
    'standard': ['Termite Spot Treatment', 'Termite'],
    'premium': ['Termite Spot Treatment', 'Termite'],
  },
  'bedbugs': {
    'standard': ['Bed Bugs'],
    'premium': ['Bed Bugs'],
  },
};

/// Website pest slug → fallback service_type when no Pricing Master row matched.
/// Prefer the matched rate's servicePackage (see serviceTypeLabelForQuote).
const Map<String, String> pestServiceLabels = {
  'cockroach-ants': 'Cockroach Standard',
  'mosquito': 'Mosquito Control',
  'termite': 'Termite Control',
  'rodent': 'Rodent / Rat Control',
  'bedbugs': 'Bed Bug Control',
  'honey-bee': 'Honey Bee / Wasp Removal',
  'wood-borer': 'Wood Borer Control',
  'house-fly': 'Fly Control',
  'hotel-commercial': 'General Pest Control',
  'other': 'General Pest Control',
};

/// Build JobCard.service_type from matched catalog package(s), not marketing copy.
String serviceTypeLabelForQuote(
  List<String> pestTypes,
  CatalogRate? matchedRate, {
  String treatmentQuality = 'standard',
}) {
  final pkg = matchedRate?.servicePackage.trim() ?? '';
  if (pkg.isNotEmpty) return pkg;

  if (pestTypes.length == 1 && pestTypes.first == 'cockroach-ants') {
    return treatmentQuality == 'premium' ? 'Cockroach Premium' : 'Cockroach Standard';
  }

  return pestTypes.map((p) => pestServiceLabels[p] ?? p).join(', ');
}

const Map<String, String> premiseSizeToArea = {
  '1rk': '1 RK',
  '1bhk': '1 BHK',
  '2bhk': '2 BHK',
  '3bhk': '3 BHK',
  '4bhk': '4 BHK',
  '5bhk': '5 BHK',
  '6bhk': '6 BHK',
  'other': 'Other',
};

const Set<String> _nonHomeCategories = {
  'addon',
  'society',
  'hotel',
  'hospital',
  'corporate',
  'commercial',
  'chain',
};

/// Display-only list markup (~30% OFF badge).
const double quoteDisplayDiscount = 0.3;

class QuotePriceResult {
  const QuotePriceResult({
    required this.listPrice,
    required this.offerPrice,
    required this.discountPercent,
    required this.pricingRateId,
    required this.pricePending,
    required this.matchedRate,
    required this.serviceTypeLabel,
    required this.packageTier,
  });

  final double listPrice;
  final double offerPrice;
  final int discountPercent;
  final int? pricingRateId;
  final bool pricePending;
  final CatalogRate? matchedRate;
  final String serviceTypeLabel;
  final String packageTier;
}

bool packageTokenMatches(List<String> keys, String servicePackage) {
  final pkg = servicePackage;
  for (final key in keys) {
    final k = key.trim().toLowerCase();
    if (k.isEmpty) continue;
    final escaped = RegExp.escape(k).replaceAll(RegExp(r'\s+'), r'\s+');
    final re = RegExp('(^|[^a-z0-9])$escaped([^a-z0-9]|\$)', caseSensitive: false);
    if (re.hasMatch(pkg)) return true;
  }
  return false;
}

bool isHomeExcludedRate(CatalogRate rate) {
  final cat = (rate.propertyCategory ?? '').toLowerCase().trim();
  if (_nonHomeCategories.contains(cat)) return true;

  final pkg = rate.servicePackage.toLowerCase();
  if (pkg.contains('integrated ipm')) return true;
  if (pkg.contains('fly catcher')) return true;
  if (pkg.contains('add-on') || pkg.contains('addon')) return true;
  if (RegExp(r'\bsociety\b').hasMatch(pkg)) return true;
  if (pkg.contains('servicing') && pkg.contains('fly')) return true;
  return false;
}

bool _planMatches(CatalogRate rate, {required bool isAmc}) {
  final plan = rate.planType.toLowerCase();
  final amc = plan.contains('amc');
  return isAmc ? amc : !amc;
}

String areaKeyForForm(String premiseType, String? premiseSize) {
  if (premiseType == 'commercial') return 'Commercial';
  if (premiseSize == null || premiseSize.isEmpty) return '';
  return premiseSizeToArea[premiseSize] ?? premiseSize;
}

List<CatalogRate> _preferNamedPackages(
  List<CatalogRate> pool,
  String pestSlug,
  String? treatmentQuality,
) {
  final prefs = pestPreferredPackages[pestSlug];
  if (prefs == null || pool.isEmpty) return pool;
  final quality = treatmentQuality == 'premium' ? 'premium' : 'standard';
  final names = prefs[quality] ?? prefs['standard'] ?? const <String>[];
  for (final name in names) {
    final hits = pool
        .where((r) => r.servicePackage.toLowerCase() == name.toLowerCase())
        .toList();
    if (hits.isNotEmpty) return hits;
  }
  return pool;
}

CatalogRate? matchRateForPest(
  List<CatalogRate> rates,
  String pestSlug, {
  required bool isAmc,
  required String premiseType,
  String? premiseSize,
  String? treatmentQuality,
}) {
  final keys = pestMatchKeys[pestSlug];
  if (keys == null || rates.isEmpty) return null;

  final isHome = premiseType != 'commercial';
  final area = areaKeyForForm(premiseType, premiseSize).toLowerCase();

  var candidates =
      rates.where((r) => packageTokenMatches(keys, r.servicePackage)).toList();
  if (candidates.isEmpty) return null;

  if (isHome) {
    candidates = candidates.where((r) => !isHomeExcludedRate(r)).toList();
    if (candidates.isEmpty) return null;
  }

  final byPlan = candidates.where((r) => _planMatches(r, isAmc: isAmc)).toList();
  var pool = byPlan.isNotEmpty ? byPlan : candidates;

  if (treatmentQuality != null && treatmentQuality.isNotEmpty) {
    final quality = treatmentQuality.toLowerCase();
    final qualityHits = pool
        .where((r) => r.servicePackage.toLowerCase().contains(quality))
        .toList();
    if (qualityHits.isNotEmpty) {
      pool = qualityHits;
    } else if (quality == 'standard') {
      final nonPremium = pool
          .where((r) => !r.servicePackage.toLowerCase().contains('premium'))
          .toList();
      if (nonPremium.isNotEmpty) pool = nonPremium;
    }
  }

  pool = _preferNamedPackages(pool, pestSlug, treatmentQuality);

  if (area.isNotEmpty) {
    final exact = pool.where((r) => r.areaKey.toLowerCase() == area).toList();
    if (exact.isNotEmpty) return exact.first;
    final soft = pool.where((r) {
      final key = r.areaKey.toLowerCase();
      return key.contains(area) || area.contains(key);
    }).toList();
    if (soft.isNotEmpty) return soft.first;
    if (isHome) return null;
  }

  if (isHome) {
    final residential = pool.where((r) {
      final cat = (r.propertyCategory ?? '').toLowerCase();
      final key = r.areaKey.toLowerCase();
      return cat.contains('residential') || key.contains('bhk') || key.contains('rk');
    }).toList();
    if (residential.isNotEmpty) return residential.first;
    return null;
  }

  final commercial = pool.where((r) {
    final cat = (r.propertyCategory ?? '').toLowerCase();
    final key = r.areaKey.toLowerCase();
    return cat.contains('commercial') || key == 'commercial';
  }).toList();
  if (commercial.isNotEmpty) return commercial.first;

  return pool.isNotEmpty ? pool.first : null;
}

double exclGstBaseAmount(CatalogRate? rate) {
  if (rate == null) return 0;
  final fromBase = double.tryParse(rate.baseAmount ?? '') ?? 0;
  if (fromBase > 0) return fromBase;

  final raw = double.tryParse(rate.amount) ?? 0;
  if (raw <= 0) return 0;

  if (rate.priceIncludesGst == true) {
    final pct = double.tryParse(rate.gstPercent ?? '18') ?? 18;
    final divisor = 1 + (pct > 0 ? pct / 100 : 0.18);
    return ((raw / divisor) * 100).round() / 100;
  }
  return raw;
}

double tierAmount(
  CatalogRate? rate, {
  String treatmentQuality = 'standard',
}) {
  if (rate == null) return 0;
  final base = exclGstBaseAmount(rate);
  if (base <= 0) return 0;
  if (treatmentQuality == 'premium') {
    return ((base * 1.15) * 100).round() / 100;
  }
  return base;
}

({double amount, String packageTier}) resolveTierForMatchedRate(
  CatalogRate? rate, {
  String treatmentQuality = 'standard',
}) {
  if (rate == null) {
    return (amount: 0, packageTier: treatmentQuality);
  }
  final pkg = rate.servicePackage.toLowerCase();
  final namedPremium = pkg.contains('premium');
  final namedStandard = pkg.contains('standard');
  if (namedPremium || namedStandard) {
    return (amount: tierAmount(rate, treatmentQuality: 'standard'), packageTier: 'standard');
  }
  return (
    amount: tierAmount(rate, treatmentQuality: treatmentQuality),
    packageTier: treatmentQuality,
  );
}

double displayListFromOffer(double offerPrice) {
  if (offerPrice <= 0) return 0;
  final list = (offerPrice / (1 - quoteDisplayDiscount)).roundToDouble();
  return list > offerPrice ? list : 0;
}

QuotePriceResult calculateCatalogQuotePrice({
  required List<CatalogRate> rates,
  required List<String> pestTypes,
  String? premiseType,
  String? premiseSize,
  String? serviceType,
  String? treatmentQuality,
}) {
  QuotePriceResult pending([String packageTier = 'standard']) {
    return QuotePriceResult(
      listPrice: 0,
      offerPrice: 0,
      discountPercent: 0,
      pricingRateId: null,
      pricePending: true,
      matchedRate: null,
      serviceTypeLabel: serviceTypeLabelForQuote(
        pestTypes,
        null,
        treatmentQuality: treatmentQuality == 'premium' ? 'premium' : 'standard',
      ),
      packageTier: packageTier,
    );
  }

  if (premiseType == null ||
      premiseType.isEmpty ||
      pestTypes.isEmpty) {
    return pending();
  }

  final isInspection =
      premiseType == 'commercial' || pestTypes.contains('hotel-commercial');
  if (isInspection) return pending();

  if (premiseSize == null ||
      premiseSize.isEmpty ||
      serviceType == null ||
      serviceType.isEmpty) {
    return pending(treatmentQuality == 'premium' ? 'premium' : 'standard');
  }

  // Default to standard when treatment quality is hidden (non-cockroach path).
  final quality = treatmentQuality == 'premium' ? 'premium' : 'standard';
  final isAmc = serviceType == 'amc';
  var total = 0.0;
  var anyMissing = false;
  CatalogRate? firstRate;
  var packageTier = quality;

  for (final pest in pestTypes) {
    final rate = matchRateForPest(
      rates,
      pest,
      isAmc: isAmc,
      premiseType: premiseType,
      premiseSize: premiseSize,
      treatmentQuality: quality,
    );
    final resolved = resolveTierForMatchedRate(rate, treatmentQuality: quality);
    if (rate == null || resolved.amount <= 0) {
      anyMissing = true;
      continue;
    }
    if (firstRate == null) {
      firstRate = rate;
      packageTier = resolved.packageTier;
    }
    total += resolved.amount;
  }

  final pricePending = anyMissing || total <= 0 || firstRate == null;
  final offerPrice = pricePending ? 0.0 : total.roundToDouble();
  final listPrice = displayListFromOffer(offerPrice);
  final discountPercent = listPrice > offerPrice && offerPrice > 0
      ? (((listPrice - offerPrice) / listPrice) * 100).round()
      : 0;

  return QuotePriceResult(
    listPrice: listPrice,
    offerPrice: offerPrice,
    discountPercent: discountPercent,
    pricingRateId: pricePending ? null : firstRate.id,
    pricePending: pricePending,
    matchedRate: firstRate,
    serviceTypeLabel: serviceTypeLabelForQuote(
      pestTypes,
      firstRate,
      treatmentQuality: quality,
    ),
    packageTier: pricePending ? quality : packageTier,
  );
}
