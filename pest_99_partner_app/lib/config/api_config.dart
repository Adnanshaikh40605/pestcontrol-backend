/// Backend API configuration — update [baseUrl] for your environment.
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.vacationbna.site',
  );

  static const String partnerPrefix = '/api/partner';

  static String get register => '$partnerPrefix/register/';
  static String get login => '$partnerPrefix/login/';
  static String get tokenRefresh => '$partnerPrefix/token/refresh/';
  static String get profile => '$partnerPrefix/profile/';
  static String get bookingCounts => '$partnerPrefix/bookings/counts/';
  static String get availableBookings => '$partnerPrefix/bookings/available/';
  static String get acceptedBookings => '$partnerPrefix/bookings/accepted/';
  static String get completedBookings => '$partnerPrefix/bookings/completed/';

  static String bookingDetail(int id) => '$partnerPrefix/bookings/$id/';
  static String acceptBooking(int id) => '$partnerPrefix/bookings/$id/accept/';
  static String rejectBooking(int id) => '$partnerPrefix/bookings/$id/reject/';
  static String startBooking(int id) => '$partnerPrefix/bookings/$id/start/';
  static String completeBooking(int id) => '$partnerPrefix/bookings/$id/complete/';
  static String get referClient => '$partnerPrefix/refer-client/';
  static String get notifications => '$partnerPrefix/notifications/';
  static String get markAllNotificationsRead => '$partnerPrefix/notifications/mark-all-read/';
  static String markNotificationRead(int id) => '$partnerPrefix/notifications/$id/read/';
}
