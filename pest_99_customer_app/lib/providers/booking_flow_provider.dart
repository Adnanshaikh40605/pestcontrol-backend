import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';

import '../core/booking_timezone.dart';
import '../models/customer_models.dart';
import '../utils/catalog_pricing.dart';

class PestOption {
  const PestOption({required this.value, required this.label});
  final String value;
  final String label;
}

class PremiseSizeOption {
  const PremiseSizeOption({required this.value, required this.label});
  final String value;
  final String label;
}

/// Website-aligned booking form state (single-screen Confirm Your Booking).
class BookingFlowProvider extends ChangeNotifier {
  static const pestOptions = <PestOption>[
    PestOption(value: 'cockroach-ants', label: 'Cockroach / Ants'),
    PestOption(value: 'termite', label: 'Termite'),
    PestOption(value: 'bedbugs', label: 'Bed Bugs'),
    PestOption(value: 'rodent', label: 'Rodent'),
    PestOption(value: 'mosquito', label: 'Mosquito'),
  ];

  static const premiseSizeOptions = <PremiseSizeOption>[
    PremiseSizeOption(value: '1rk', label: '1 RK'),
    PremiseSizeOption(value: '1bhk', label: '1 BHK'),
    PremiseSizeOption(value: '2bhk', label: '2 BHK'),
    PremiseSizeOption(value: '3bhk', label: '3 BHK'),
    PremiseSizeOption(value: '4bhk', label: '4 BHK'),
    PremiseSizeOption(value: '5bhk', label: '5 BHK'),
    PremiseSizeOption(value: '6bhk', label: '6 BHK'),
    PremiseSizeOption(value: 'other', label: 'Other'),
  ];

  /// Maps legacy home-tile / deep-link ids → website pest slugs.
  static const legacyServiceToPest = <String, String>{
    'cockroach': 'cockroach-ants',
    'ant': 'cockroach-ants',
    'cockroach-ants': 'cockroach-ants',
    'termite': 'termite',
    'bedbug': 'bedbugs',
    'bedbugs': 'bedbugs',
    'rodent': 'rodent',
    'mosquito': 'mosquito',
  };

  static const treatmentDetails = <String, ({String title, List<String> bullets, String? whyTitle, String? whyBody})>{
    'standard': (
      title: 'Standard Treatment',
      bullets: [
        'Strong chemical spray with standard gel treatment.',
        'Kitchen utensils and food items must be removed before treatment.',
        'Our technician can assist with utensil removal for an additional charge of ₹300.',
        'Keep children and pets away from the treated area.',
        'Do not use the treated area for at least 3 hours after treatment.',
      ],
      whyTitle: null,
      whyBody: null,
    ),
    'premium': (
      title: 'Premium Treatment — Recommended',
      bullets: [
        'Advanced premium gel treatment for complete-home cockroach control.',
        'Premium gel remains active and continuously targets hidden cockroaches.',
        'No need to remove kitchen utensils for gel-only treatment.',
        'Odourless spray with no unpleasant smell with premium gel is also available if spray treatment is required.',
        'Cockroach monitoring pads/traps will be provided wherever necessary.',
        'Tried-and-tested treatment method for effective and long-lasting control.',
        'Ideal for families looking for minimum preparation, less inconvenience and better protection.',
      ],
      whyTitle: 'Why Choose Premium?',
      whyBody:
          'Choose Premium Treatment for hassle-free service, no utensil removal and long-lasting cockroach control.',
    ),
  };

  static const otherPremiseWhatsAppMessage =
      'Hi Pest Control 99, I selected Other for premise size on the app booking form and need a custom quote.';
  static const supportPhoneTel = '+918080748282';
  static const supportWhatsApp = '918080748282';

  /// 'residential' | 'commercial'
  String premiseType = 'residential';
  final List<String> pestTypes = ['cockroach-ants'];
  String premiseSize = '';
  String treatmentQuality = '';
  String serviceType = ''; // 'one-time' | 'amc'
  String streetAddress = '';
  String fullName = '';
  String mobile = '';
  String preferredDate = '';
  String preferredTime = ''; // 12h display e.g. "02:30 PM"
  CustomerBooking? confirmedBooking;
  String? confirmedMobile;

  List<CatalogRate> rates = [];
  bool ratesLoading = false;
  String? ratesError;

  BookingFlowProvider() {
    _applyDefaultSchedule();
  }

  void _applyDefaultSchedule() {
    final now = BookingTimezone.now();
    var target = now.add(const Duration(hours: 1));
    // Round minute up to 5-min step (website ClockTimePicker).
    final rem = target.minute % 5;
    if (rem != 0) {
      target = target.add(Duration(minutes: 5 - rem));
    }
    target = DateTime(target.year, target.month, target.day, target.hour, target.minute);
    preferredDate = DateFormat('yyyy-MM-dd').format(target);
    preferredTime = _format12h(target.hour, target.minute);
  }

  static String _format12h(int hour24, int minute) {
    final period = hour24 >= 12 ? 'PM' : 'AM';
    var h = hour24 % 12;
    if (h == 0) h = 12;
    return '${h.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')} $period';
  }

  static String formatFriendlyTime(String value) {
    final m = RegExp(r'(\d{1,2}):(\d{2})\s*(AM|PM)', caseSensitive: false).firstMatch(value.trim());
    if (m == null) return value;
    final hour = int.tryParse(m.group(1)!) ?? 0;
    return '$hour:${m.group(2)} ${m.group(3)!.toLowerCase()}';
  }

  String get friendlyPreferredDate {
    if (preferredDate.isEmpty) return '';
    DateTime? date;
    try {
      date = DateTime.parse(preferredDate);
    } catch (_) {
      return '';
    }
    final today = BookingTimezone.today();
    final tomorrow = today.add(const Duration(days: 1));
    final day = DateTime(date.year, date.month, date.day);
    final mon = DateFormat('MMM').format(day);
    if (BookingTimezone.isSameDay(day, today)) {
      return 'Today • ${day.day} $mon';
    }
    if (BookingTimezone.isSameDay(day, tomorrow)) {
      return 'Tomorrow • ${day.day} $mon';
    }
    return DateFormat('d MMM yyyy').format(day);
  }

  bool get isResidential => premiseType == 'residential';
  bool get isCommercial => premiseType == 'commercial';
  bool get isInspectionQuote =>
      isCommercial || pestTypes.contains('hotel-commercial');
  bool get isOtherPremiseSize => premiseSize == 'other';
  bool get amcAvailable =>
      pestTypes.isNotEmpty && pestTypes.every((p) => p == 'cockroach-ants');

  bool get selectionsComplete {
    if (premiseType.isEmpty || pestTypes.isEmpty) return false;
    if (isInspectionQuote) return true;
    return premiseSize.isNotEmpty &&
        treatmentQuality.isNotEmpty &&
        serviceType.isNotEmpty;
  }

  QuotePriceResult get quote => calculateCatalogQuotePrice(
        rates: rates,
        pestTypes: List.unmodifiable(pestTypes),
        premiseType: premiseType,
        premiseSize: premiseSize,
        serviceType: serviceType,
        treatmentQuality: treatmentQuality,
      );

  String get priceSummaryLabel {
    if (!selectionsComplete) return 'Select options for price';
    if (isOtherPremiseSize) return 'Custom quote — call / WhatsApp';
    if (isInspectionQuote) return 'Site inspection';
    final quality = treatmentQuality == 'premium' ? 'Premium' : 'Standard';
    if (serviceType == 'amc') return '$quality AMC • 3 visits';
    if (serviceType == 'one-time') return '$quality • One-Time';
    return 'Select options for price';
  }

  String get serviceTypeLabel => quote.serviceTypeLabel;

  String get propertyTypeForApi =>
      isCommercial ? 'Commercial Space' : 'Home / Flat';

  String get bhkSizeForApi {
    if (isCommercial) return 'Commercial';
    return areaKeyForForm(premiseType, premiseSize);
  }

  String get bookingTypeForApi {
    if (isInspectionQuote) return 'one_time';
    return serviceType == 'amc' ? 'amc' : 'one_time';
  }

  (int hour, int minute)? get preferredTimeParts {
    final m = RegExp(r'(\d{1,2}):(\d{2})\s*(AM|PM)', caseSensitive: false)
        .firstMatch(preferredTime.trim());
    if (m == null) return null;
    var hour = int.tryParse(m.group(1)!) ?? 0;
    final minute = int.tryParse(m.group(2)!) ?? 0;
    final meridiem = (m.group(3) ?? 'AM').toUpperCase();
    if (meridiem == 'PM' && hour < 12) hour += 12;
    if (meridiem == 'AM' && hour == 12) hour = 0;
    return (hour, minute);
  }

  String? get bookingTime24 {
    final parts = preferredTimeParts;
    if (parts == null) return null;
    return '${parts.$1.toString().padLeft(2, '0')}:${parts.$2.toString().padLeft(2, '0')}';
  }

  String get timeSlotLabel => formatFriendlyTime(preferredTime);

  void setPremiseType(String value) {
    if (premiseType == value) return;
    premiseType = value;
    if (value == 'commercial') {
      treatmentQuality = '';
      serviceType = '';
      premiseSize = '';
    }
    notifyListeners();
  }

  void setPestTypes(List<String> values) {
    pestTypes
      ..clear()
      ..addAll(values.where((v) => v != 'hotel-commercial'));
    if (!amcAvailable && serviceType == 'amc') {
      serviceType = '';
    }
    notifyListeners();
  }

  void togglePest(String value) {
    if (pestTypes.contains(value)) {
      pestTypes.remove(value);
    } else {
      pestTypes.add(value);
    }
    pestTypes.remove('hotel-commercial');
    if (!amcAvailable && serviceType == 'amc') {
      serviceType = '';
    }
    notifyListeners();
  }

  void setPremiseSize(String value) {
    premiseSize = value;
    notifyListeners();
  }

  void setTreatmentQuality(String value) {
    treatmentQuality = value;
    notifyListeners();
  }

  void setServiceType(String value) {
    if (value == 'amc' && !amcAvailable) return;
    serviceType = value;
    notifyListeners();
  }

  void setStreetAddress(String value) {
    streetAddress = value;
    notifyListeners();
  }

  void setFullName(String value) {
    fullName = value;
    notifyListeners();
  }

  void setMobile(String value) {
    final digits = value.replaceAll(RegExp(r'\D'), '');
    mobile = digits.length > 10 ? digits.substring(0, 10) : digits;
    notifyListeners();
  }

  void setPreferredDate(DateTime date) {
    preferredDate = DateFormat('yyyy-MM-dd').format(
      DateTime(date.year, date.month, date.day),
    );
    notifyListeners();
  }

  void setPreferredTime(int hour24, int minute) {
    preferredTime = _format12h(hour24.clamp(0, 23), minute.clamp(0, 59));
    notifyListeners();
  }

  /// Prefill from home popular tile / deep link.
  void beginWithService(String id) {
    final slug = legacyServiceToPest[id] ?? id;
    pestTypes
      ..clear()
      ..add(slug);
    if (!amcAvailable && serviceType == 'amc') serviceType = '';
    notifyListeners();
  }

  void setConfirmed(CustomerBooking booking, {String? mobileOverride}) {
    confirmedBooking = booking;
    confirmedMobile = mobileOverride ?? mobile;
    notifyListeners();
  }

  // Optional place/geo fields (website payload supports lat/lng).
  double? serviceLatitude;
  double? serviceLongitude;
  String serviceCity = '';
  String serviceArea = '';
  String serviceFullAddress = '';
  String servicePlaceId = '';
  int? masterCityId;
  int? masterLocationId;

  /// Compatibility for legacy ServiceAddressSection widget (unused by new form).
  String get serviceAddress => streetAddress;
  DateTime get selectedDate {
    final parsed = DateTime.tryParse(preferredDate);
    return parsed ?? BookingTimezone.today();
  }

  String get selectedSlot => timeSlotLabel;
  int get selectedHour => preferredTimeParts?.$1 ?? 10;
  int get selectedMinute => preferredTimeParts?.$2 ?? 0;

  void setTime(int hour24, int minute) => setPreferredTime(hour24, minute);

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
    if (address != null) streetAddress = address;
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
    premiseType = 'residential';
    pestTypes
      ..clear()
      ..add('cockroach-ants');
    premiseSize = '';
    treatmentQuality = '';
    serviceType = '';
    streetAddress = '';
    fullName = '';
    mobile = '';
    confirmedBooking = null;
    confirmedMobile = null;
    serviceLatitude = null;
    serviceLongitude = null;
    serviceCity = '';
    serviceArea = '';
    serviceFullAddress = '';
    servicePlaceId = '';
    masterCityId = null;
    masterLocationId = null;
    _applyDefaultSchedule();
    notifyListeners();
  }

  /// Client-side validation matching website home form.
  Map<String, String> validate() {
    final errors = <String, String>{};
    if (premiseType != 'residential' && premiseType != 'commercial') {
      errors['premiseType'] = 'Please select Residential or Commercial';
    }
    if (pestTypes.isEmpty) {
      errors['pestTypes'] = 'Please select at least one service';
    }
    if (!isInspectionQuote) {
      if (premiseSize.isEmpty) {
        errors['premiseSize'] = 'Please select a premise size';
      }
      if (treatmentQuality != 'standard' && treatmentQuality != 'premium') {
        errors['treatmentQuality'] = 'Please select treatment quality';
      }
      if (serviceType != 'amc' && serviceType != 'one-time') {
        errors['serviceType'] = 'Please select a service plan';
      }
    }
    if (streetAddress.trim().length < 5) {
      errors['streetAddress'] = 'Please enter your service address';
    }
    if (preferredDate.trim().isEmpty) {
      errors['preferredDate'] = 'Please select a preferred date';
    }
    if (bookingTime24 == null) {
      errors['preferredTime'] = 'Please select a preferred time';
    }
    if (fullName.trim().length < 2) {
      errors['name'] = 'Name must be at least 2 characters long';
    }
    if (mobile.replaceAll(RegExp(r'\D'), '').length != 10) {
      errors['phone'] = 'Phone number must be exactly 10 digits';
    }
    return errors;
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

  // ── Legacy aliases used by older screens / tests (kept for compile safety) ──
  @Deprecated('Use pestTypes')
  Set<String> get selectedServiceIds => pestTypes.toSet();

  @Deprecated('Use isResidential')
  bool get isHome => isResidential;

  @Deprecated('Removed multi-step lock')
  String? get lockedServiceId => null;

  @Deprecated('Removed multi-step lock')
  bool get isServiceLocked => false;
}
