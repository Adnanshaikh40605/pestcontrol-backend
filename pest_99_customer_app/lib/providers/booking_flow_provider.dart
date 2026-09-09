import 'package:flutter/foundation.dart';

import '../core/booking_timezone.dart';
import '../models/customer_models.dart';

class ServiceOption {
  const ServiceOption({
    required this.id,
    required this.name,
    required this.icon,
    required this.matchKeys,
  });

  final String id;
  final String name;
  final String icon;
  /// Keywords used to match CRM `service_package` names.
  final List<String> matchKeys;
}

class BookingFlowProvider extends ChangeNotifier {
  /// Home tab — BHK / property size options (plus Custom).
  static const homeBhkOptions = <String>[
    '1 RK',
    '1 BHK',
    '2 BHK',
    '3 BHK',
    '4 BHK',
    '5 BHK',
    'Bungalow / Villa',
    'Custom',
  ];

  /// Commercial tab — property type options (plus Other).
  static const commercialOptions = <String>[
    'Office',
    'Shop',
    'Restaurant',
    'Hotel',
    'Society',
    'School',
    'Hospital',
    'Warehouse',
    'Factory',
    'Other',
  ];

  static const catalog = <ServiceOption>[
    ServiceOption(id: 'cockroach', name: 'Cockroach Control', icon: 'cockroach', matchKeys: ['cockroach']),
    ServiceOption(id: 'ant', name: 'Ant Control', icon: 'ant', matchKeys: ['ant']),
    ServiceOption(id: 'mosquito', name: 'Mosquito Control', icon: 'mosquito', matchKeys: ['mosquito']),
    ServiceOption(id: 'termite', name: 'Termite Control', icon: 'termite', matchKeys: ['termite']),
    ServiceOption(id: 'bedbug', name: 'Bed Bug Control', icon: 'bedbug', matchKeys: ['bed bug', 'bedbug', 'bed bugs']),
    ServiceOption(id: 'rodent', name: 'Rodent / Rat Control', icon: 'rodent', matchKeys: ['rodent', 'rat']),
    ServiceOption(id: 'fly', name: 'Fly Control', icon: 'fly', matchKeys: ['fly', 'flies']),
    ServiceOption(id: 'lizard', name: 'Lizard Control', icon: 'lizard', matchKeys: ['lizard']),
    ServiceOption(id: 'spider', name: 'Spider Control', icon: 'spider', matchKeys: ['spider']),
    ServiceOption(id: 'woodborer', name: 'Wood Borer Control', icon: 'woodborer', matchKeys: ['wood borer', 'woodborer', 'borer']),
    ServiceOption(id: 'bee', name: 'Honey Bee / Wasp Removal', icon: 'bee', matchKeys: ['bee', 'wasp']),
    ServiceOption(id: 'general', name: 'General Pest Control', icon: 'general', matchKeys: ['general']),
  ];

  /// Plan options allowed per service catalog id.
  static List<String> planOptionsFor(String serviceId) {
    switch (serviceId) {
      case 'bedbug':
        return const ['2_service'];
      case 'termite':
        return const ['one_time'];
      case 'general':
      case 'cockroach':
      case 'ant':
      case 'rodent':
      case 'mosquito':
        return const ['one_time', 'amc'];
      default:
        return const ['one_time'];
    }
  }

  /// 'home' | 'commercial'
  String propertyCategory = 'home';
  String? homeBhk;
  String? commercialType;
  String customConfig = '';

  final Set<String> selectedServiceIds = {};
  final Map<String, bool> planIsAmc = {};

  /// When set (from Home `?service=` or popular tap), only this service is shown.
  String? lockedServiceId;

  DateTime selectedDate = BookingTimezone.today();
  int selectedHour = 10;
  int selectedMinute = 0;
  CustomerBooking? confirmedBooking;

  String serviceAddress = '';
  String serviceCity = '';
  String serviceArea = '';
  String serviceFullAddress = '';
  String servicePlaceId = '';
  int? masterCityId;
  int? masterLocationId;
  double? serviceLatitude;
  double? serviceLongitude;

  BookingFlowProvider() {
    final t = BookingTimezone.defaultTimeFor(selectedDate);
    selectedHour = t.$1;
    selectedMinute = t.$2;
  }

  /// 12h display label for the selected time (e.g. "02:30 PM").
  String get selectedSlot => BookingTimezone.format12h(selectedHour, selectedMinute);

  bool get hasValidSelectedTime =>
      BookingTimezone.isWithinServiceWindow(selectedHour, selectedMinute) &&
      BookingTimezone.isNotInPast(selectedDate, selectedHour, selectedMinute);

  List<CatalogRate> rates = [];
  bool ratesLoading = false;
  String? ratesError;

  bool get isHome => propertyCategory == 'home';

  bool get _needsCustomText =>
      (isHome && homeBhk == 'Custom') || (!isHome && commercialType == 'Other');

  /// Effective property size / type label for the current selection.
  String? get propertyConfig {
    final base = isHome ? homeBhk : commercialType;
    if (base == null) return null;
    if (_needsCustomText) {
      final txt = customConfig.trim();
      if (txt.isEmpty) return null;
      return isHome ? '$txt BHK' : txt;
    }
    return base;
  }

  bool get propertySelected => propertyConfig != null;

  String get propertyLabel =>
      isHome ? 'Home (Residential)' : 'Commercial Property';

  String get propertyTypeForApi => isHome ? 'Home / Flat' : (propertyConfig ?? 'Commercial');

  String get bhkSizeForApi => isHome ? (propertyConfig ?? '') : 'Commercial';

  List<ServiceOption> get selectedServices =>
      catalog.where((s) => selectedServiceIds.contains(s.id)).toList();

  bool get isServiceLocked => lockedServiceId != null;

  ServiceOption? get lockedService =>
      lockedServiceId != null ? serviceById(lockedServiceId!) : null;

  /// Services shown on the booking page — filtered by lock and backend catalog rates.
  List<ServiceOption> get visibleCatalog {
    if (lockedServiceId != null) {
      final locked = serviceById(lockedServiceId!);
      if (locked != null) return [locked];
    }
    return catalogFromRates;
  }

  /// Catalog entries that have at least one matching CRM rate (when rates are loaded).
  List<ServiceOption> get catalogFromRates {
    if (rates.isEmpty) return catalog;
    final matched = catalog
        .where((s) => rates.any((r) => _packageMatches(s, r.servicePackage)))
        .toList();
    return matched.isNotEmpty ? matched : catalog;
  }

  void setCategory(String category) {
    if (propertyCategory == category) return;
    propertyCategory = category;
    notifyListeners();
  }

  void selectHomeBhk(String value) {
    homeBhk = value;
    notifyListeners();
  }

  void selectCommercialType(String value) {
    commercialType = value;
    notifyListeners();
  }

  void setCustomConfig(String value) {
    customConfig = value;
    notifyListeners();
  }

  void toggleService(String id) {
    if (selectedServiceIds.contains(id)) {
      selectedServiceIds.remove(id);
      planIsAmc.remove(id);
    } else {
      selectedServiceIds.add(id);
      final options = planOptionsFor(id);
      planIsAmc[id] = options.contains('amc') && options.first == 'amc';
      if (options.contains('2_service')) {
        planIsAmc[id] = false; // Bed Bugs uses one-time package path with 2 visits
      }
    }
    notifyListeners();
  }

  /// Start booking from Home with one service locked for the whole flow.
  void beginWithService(String id) {
    lockedServiceId = id;
    selectOnlyService(id);
  }

  /// Start booking flow with a single popular service pre-selected.
  void selectOnlyService(String id) {
    selectedServiceIds
      ..clear()
      ..add(id);
    planIsAmc.clear();
    final options = planOptionsFor(id);
    planIsAmc[id] = options.contains('amc') && options.first == 'amc';
    if (options.contains('2_service')) {
      planIsAmc[id] = false;
    }
    notifyListeners();
  }

  /// Allow picking a different service (clears Home lock + selection).
  void unlockServiceSelection() {
    lockedServiceId = null;
    selectedServiceIds.clear();
    planIsAmc.clear();
    notifyListeners();
  }

  void setPlan(String serviceId, {required bool isAmc}) {
    final options = planOptionsFor(serviceId);
    if (isAmc && !options.contains('amc')) return;
    if (!isAmc && !options.contains('one_time') && !options.contains('2_service')) return;
    planIsAmc[serviceId] = isAmc;
    notifyListeners();
  }

  String planLabel(String serviceId) {
    final options = planOptionsFor(serviceId);
    if (options.length == 1 && options.first == '2_service') {
      return '2-Service Package';
    }
    if (options.length == 1 && options.first == 'one_time') {
      return 'One-Time Service';
    }
    final isAmc = planIsAmc[serviceId] ?? false;
    final rate = matchRateForService(serviceId, isAmc: isAmc);
    if (rate != null && rate.planType.trim().isNotEmpty) {
      return rate.planType;
    }
    return isAmc ? 'AMC Package' : 'One-Time Service';
  }

  void setDate(DateTime date) {
    selectedDate = DateTime(date.year, date.month, date.day);
    // Keep time if still valid; otherwise bump to a sensible default for the day.
    if (!hasValidSelectedTime) {
      final t = BookingTimezone.defaultTimeFor(selectedDate);
      selectedHour = t.$1;
      selectedMinute = t.$2;
    }
    notifyListeners();
  }

  void setTime(int hour24, int minute) {
    selectedHour = hour24.clamp(0, 23);
    selectedMinute = minute.clamp(0, 59);
    notifyListeners();
  }

  /// Legacy alias — parses a 12h label if needed.
  void setSlot(String slot) {
    final match = RegExp(r'(\d{1,2}):(\d{2})\s*(AM|PM)', caseSensitive: false).firstMatch(slot);
    if (match == null) return;
    var hour = int.tryParse(match.group(1)!) ?? 10;
    final minute = int.tryParse(match.group(2)!) ?? 0;
    final meridiem = (match.group(3) ?? 'AM').toUpperCase();
    if (meridiem == 'PM' && hour < 12) hour += 12;
    if (meridiem == 'AM' && hour == 12) hour = 0;
    setTime(hour, minute);
  }

  void setServiceAddress({
    String? address,
    String? city,
    String? area,
    String? fullAddress,
    String? placeId,
    int? masterCityId,
    int? masterLocationId,
    double? latitude,
    double? longitude,
    bool clearLocationIds = false,
    bool clearPlaceId = false,
  }) {
    if (address != null) serviceAddress = address;
    if (city != null) serviceCity = city;
    if (area != null) serviceArea = area;
    if (fullAddress != null) serviceFullAddress = fullAddress;
    if (placeId != null) servicePlaceId = placeId;
    if (clearPlaceId) servicePlaceId = '';
    if (clearLocationIds) {
      this.masterCityId = null;
      this.masterLocationId = null;
      serviceArea = '';
    }
    if (masterCityId != null) this.masterCityId = masterCityId;
    if (masterLocationId != null) this.masterLocationId = masterLocationId;
    if (latitude != null) serviceLatitude = latitude;
    if (longitude != null) serviceLongitude = longitude;
    notifyListeners();
  }

  void clearMasterLocation() {
    masterLocationId = null;
    serviceArea = '';
    notifyListeners();
  }

  bool get hasServiceAddress =>
      serviceAddress.trim().length >= 5 &&
      masterCityId != null &&
      masterLocationId != null;

  void setConfirmed(CustomerBooking booking) {
    confirmedBooking = booking;
    notifyListeners();
  }

  void setRates(List<CatalogRate> value) {
    rates = value;
    ratesLoading = false;
    ratesError = null;
    notifyListeners();
  }

  void setRatesLoading(bool value) {
    ratesLoading = value;
    if (value) ratesError = null;
    notifyListeners();
  }

  void setRatesError(String message) {
    ratesLoading = false;
    ratesError = message;
    notifyListeners();
  }

  void resetFlow() {
    propertyCategory = 'home';
    homeBhk = null;
    commercialType = null;
    customConfig = '';
    lockedServiceId = null;
    selectedServiceIds.clear();
    planIsAmc.clear();
    selectedDate = BookingTimezone.today();
    final t = BookingTimezone.defaultTimeFor(selectedDate);
    selectedHour = t.$1;
    selectedMinute = t.$2;
    confirmedBooking = null;
    serviceAddress = '';
    serviceCity = '';
    serviceArea = '';
    serviceFullAddress = '';
    servicePlaceId = '';
    masterCityId = null;
    masterLocationId = null;
    serviceLatitude = null;
    serviceLongitude = null;
    notifyListeners();
  }

  ServiceOption? serviceById(String id) {
    for (final s in catalog) {
      if (s.id == id) return s;
    }
    return null;
  }

  bool _packageMatches(ServiceOption service, String package) {
    final p = package.toLowerCase();
    for (final key in service.matchKeys) {
      if (p.contains(key.toLowerCase())) return true;
    }
    return false;
  }

  bool _planMatches(CatalogRate rate, {required bool isAmc}) {
    final plan = rate.planType.toLowerCase();
    final amc = plan.contains('amc');
    return isAmc ? amc : !amc;
  }

  String get _areaLookup {
    if (!isHome) return 'Commercial';
    return propertyConfig ?? '';
  }

  /// Best CRM rate for one selected service + plan + property size.
  CatalogRate? matchRateForService(String serviceId, {bool? isAmc}) {
    final service = serviceById(serviceId);
    if (service == null || rates.isEmpty) return null;
    final wantAmc = isAmc ?? (planIsAmc[serviceId] ?? false);
    final area = _areaLookup.toLowerCase();

    final byService = rates.where((r) => _packageMatches(service, r.servicePackage)).toList();
    if (byService.isEmpty) return null;

    final byPlan = byService.where((r) => _planMatches(r, isAmc: wantAmc)).toList();
    final pool = byPlan.isNotEmpty ? byPlan : byService;

    if (area.isNotEmpty) {
      final exact = pool.where((r) => r.areaKey.toLowerCase() == area).toList();
      if (exact.isNotEmpty) return exact.first;
      final soft = pool.where((r) => r.areaKey.toLowerCase().contains(area) || area.contains(r.areaKey.toLowerCase())).toList();
      if (soft.isNotEmpty) return soft.first;
    }

    // Prefer residential rates for home; commercial key for commercial.
    if (isHome) {
      final residential = pool.where((r) {
        final cat = (r.propertyCategory ?? '').toLowerCase();
        final key = r.areaKey.toLowerCase();
        return cat.contains('residential') || key.contains('bhk') || key.contains('rk');
      }).toList();
      if (residential.isNotEmpty) return residential.first;
    } else {
      final commercial = pool.where((r) {
        final cat = (r.propertyCategory ?? '').toLowerCase();
        final key = r.areaKey.toLowerCase();
        return cat.contains('commercial') || key == 'commercial';
      }).toList();
      if (commercial.isNotEmpty) return commercial.first;
    }

    return pool.first;
  }

  /// Primary rate used when confirming (first selected service).
  CatalogRate? matchRate([List<CatalogRate>? override]) {
    if (override != null && override.isNotEmpty) {
      rates = override;
    }
    if (selectedServiceIds.isEmpty) return null;
    return matchRateForService(selectedServiceIds.first);
  }

  double? amountForService(String serviceId, {bool? isAmc}) {
    final rate = matchRateForService(serviceId, isAmc: isAmc);
    if (rate == null) return null;
    return double.tryParse(rate.amount);
  }

  double get estimatedTotal {
    var total = 0.0;
    var any = false;
    for (final id in selectedServiceIds) {
      final amount = amountForService(id);
      if (amount != null && amount > 0) {
        total += amount;
        any = true;
      }
    }
    return any ? total : 0;
  }

  static String formatInr(num? value) {
    if (value == null) return '—';
    final n = value.round();
    final s = n.toString();
    if (s.length <= 3) return '₹$s';
    final last3 = s.substring(s.length - 3);
    var rest = s.substring(0, s.length - 3);
    final parts = <String>[];
    while (rest.length > 2) {
      parts.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) parts.insert(0, rest);
    return '₹${parts.join(',')},$last3';
  }

  String priceLabelForService(String serviceId, {bool? isAmc}) {
    final amount = amountForService(serviceId, isAmc: isAmc);
    if (amount == null) return 'Price on request';
    if (amount <= 0) return 'After inspection';
    return formatInr(amount);
  }
}
