/// Backend API configuration for the customer app.
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.vacationbna.site',
  );

  /// Public force-update policy for the customer app.
  static const String appVersion = '/api/app/version/?app=customer';

  static const String prefix = '/api/customer';

  static String get otpSend => '$prefix/otp/send/';
  static String get otpVerify => '$prefix/otp/verify/';
  static String get tokenRefresh => '$prefix/token/refresh/';
  static String get profile => '$prefix/profile/';
  static String get profileDelete => '$prefix/profile/delete/';
  static String get complaints => '$prefix/complaints/';
  static String get catalog => '$prefix/catalog/';
  static String get bookings => '$prefix/bookings/';
  static String bookingDetail(int id) => '$prefix/bookings/$id/';
  static String bookingPay(int id) => '$prefix/bookings/$id/pay/';
  static String bookingRate(int id) => '$prefix/bookings/$id/rate/';
  static String bookingInvoice(int id) => '$prefix/bookings/$id/invoice/';
  static String get history => '$prefix/history/';
  static String get amcSchedule => '$prefix/amc-schedule/';
}
