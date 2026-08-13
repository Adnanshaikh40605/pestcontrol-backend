import '../config/api_config.dart';
import '../core/api_client.dart';
import '../models/customer_models.dart';

class AuthService {
  AuthService(this._api);
  final ApiClient _api;

  Future<Map<String, dynamic>> sendOtp({
    required String mobile,
    required String purpose,
    String fullName = '',
  }) {
    return _api.post(
      ApiConfig.otpSend,
      auth: false,
      body: {
        'mobile': mobile,
        'purpose': purpose,
        if (fullName.isNotEmpty) 'full_name': fullName,
      },
    );
  }

  Future<CustomerProfile> verifyOtp({
    required String mobile,
    required String otp,
    required String purpose,
    String fullName = '',
  }) async {
    final data = await _api.post(
      ApiConfig.otpVerify,
      auth: false,
      body: {
        'mobile': mobile,
        'otp': otp,
        'purpose': purpose,
        if (fullName.isNotEmpty) 'full_name': fullName,
      },
    );
    await _api.saveTokens(
      access: data['access'] as String,
      refresh: data['refresh'] as String,
    );
    return CustomerProfile.fromJson(data['customer'] as Map<String, dynamic>);
  }

  Future<void> logout() => _api.clearTokens();

  Future<CustomerProfile> getProfile() async {
    final data = await _api.get(ApiConfig.profile);
    return CustomerProfile.fromJson(data['customer'] as Map<String, dynamic>);
  }

  Future<CustomerProfile> updateProfile({String? fullName, String? email}) async {
    final data = await _api.put(
      ApiConfig.profile,
      body: {
        if (fullName != null) 'full_name': fullName,
        if (email != null) 'email': email,
      },
    );
    return CustomerProfile.fromJson(data['customer'] as Map<String, dynamic>);
  }

  Future<void> deleteAccount() async {
    await _api.post(ApiConfig.profileDelete, body: {'confirm': true});
    await _api.clearTokens();
  }
}

class CatalogService {
  CatalogService(this._api);
  final ApiClient _api;

  Future<List<CatalogRate>> list({String? city}) async {
    final path = city != null && city.isNotEmpty
        ? '${ApiConfig.catalog}?city=${Uri.encodeQueryComponent(city)}'
        : ApiConfig.catalog;
    final data = await _api.get(path, auth: false);
    final raw = data['results'];
    if (raw is! List) return [];
    return raw.whereType<Map<String, dynamic>>().map(CatalogRate.fromJson).toList();
  }
}

class SupportService {
  SupportService(this._api);
  final ApiClient _api;

  Future<CustomerBooking> submitComplaint({
    required String complaintType,
    required String note,
    int? bookingId,
  }) async {
    final data = await _api.post(
      ApiConfig.complaints,
      body: {
        'complaint_type': complaintType,
        'note': note,
        if (bookingId != null) 'booking_id': bookingId,
      },
    );
    return CustomerBooking.fromJson(data['booking'] as Map<String, dynamic>);
  }
}

class BookingService {
  BookingService(this._api);
  final ApiClient _api;

  Future<List<CustomerBooking>> list() async {
    final data = await _api.get(ApiConfig.bookings);
    final raw = data['results'];
    if (raw is! List) return [];
    return raw.whereType<Map<String, dynamic>>().map(CustomerBooking.fromJson).toList();
  }

  Future<CustomerBooking> detail(int id) async {
    final data = await _api.get(ApiConfig.bookingDetail(id));
    return CustomerBooking.fromJson(data);
  }

  Future<CustomerBooking> book({
    required String serviceType,
    required int pricingRateId,
    required String packageTier,
    required String address,
    String city = '',
    String area = '',
    String bhkSize = '',
    String propertyType = 'Home / Flat',
    String bookingType = 'one_time',
    String notes = '',
    String? scheduleDatetime,
    String? timeSlot,
  }) async {
    final body = <String, dynamic>{
      'service_type': serviceType,
      'package_tier': packageTier,
      'address': address,
      'property_type': propertyType,
      'booking_type': bookingType,
      if (pricingRateId > 0) 'pricing_rate_id': pricingRateId,
      if (city.isNotEmpty) 'city': city,
      if (area.isNotEmpty) 'area': area,
      if (bhkSize.isNotEmpty) 'bhk_size': bhkSize,
      if (notes.isNotEmpty) 'notes': notes,
      if (scheduleDatetime != null) 'schedule_datetime': scheduleDatetime,
      if (timeSlot != null) 'time_slot': timeSlot,
    };
    final data = await _api.post(ApiConfig.bookings, body: body);
    return CustomerBooking.fromJson(data['booking'] as Map<String, dynamic>);
  }

  Future<CustomerBooking> pay(int id, {String reference = ''}) async {
    final data = await _api.post(
      ApiConfig.bookingPay(id),
      body: {'payment_reference': reference},
    );
    return CustomerBooking.fromJson(data['booking'] as Map<String, dynamic>);
  }

  Future<void> rate(int id, {required int rating, String remark = ''}) async {
    await _api.post(
      ApiConfig.bookingRate(id),
      body: {'rating': rating, 'remark': remark, 'technician_behavior': 'good'},
    );
  }

  Future<List<CustomerBooking>> history() async {
    final data = await _api.get(ApiConfig.history);
    final raw = data['results'];
    if (raw is! List) return [];
    return raw.whereType<Map<String, dynamic>>().map(CustomerBooking.fromJson).toList();
  }

  Future<Map<String, dynamic>> invoice(int id) => _api.get(ApiConfig.bookingInvoice(id));

  Future<List<AmcScheduleGroup>> amcSchedule() async {
    final data = await _api.get(ApiConfig.amcSchedule);
    final raw = data['results'];
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(AmcScheduleGroup.fromJson)
        .toList();
  }
}
