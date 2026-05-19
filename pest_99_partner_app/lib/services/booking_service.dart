import '../config/api_config.dart';
import '../core/api_client.dart';
import '../models/booking.dart';

class BookingService {
  BookingService(this._api);

  final ApiClient _api;

  Future<BookingCounts> getCounts() async {
    final data = await _api.get(ApiConfig.bookingCounts);
    return BookingCounts.fromJson(data);
  }

  Future<List<PartnerBooking>> getAvailable() => _list(ApiConfig.availableBookings);
  Future<List<PartnerBooking>> getAccepted() => _list(ApiConfig.acceptedBookings);
  Future<List<PartnerBooking>> getCompleted() => _list(ApiConfig.completedBookings);

  Future<List<PartnerBooking>> _list(String path) async {
    final data = await _api.get(path);
    final results = data['results'] as List<dynamic>? ?? [];
    return results.map((e) => PartnerBooking.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<PartnerBooking> getDetail(int id) async {
    final data = await _api.get(ApiConfig.bookingDetail(id));
    return PartnerBooking.fromJson(data);
  }

  Future<void> accept(int id) => _api.post(ApiConfig.acceptBooking(id));

  Future<void> reject(int id, {String? reason}) =>
      _api.post(ApiConfig.rejectBooking(id), body: {'reason': reason ?? ''});

  Future<void> startWithSelfie(int id, String filePath) async {
    await _api.postMultipart(
      ApiConfig.startBooking(id),
      files: {'selfie': filePath},
    );
  }

  Future<void> complete(int id, String paymentMode) => _api.post(
        ApiConfig.completeBooking(id),
        body: {'payment_mode': paymentMode},
      );
}
