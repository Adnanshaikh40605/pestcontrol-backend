/// Backend API configuration for staff tracking app.
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.vacationbna.site',
  );

  static const String prefix = '/api/staff-tracking';

  static String get login => '$prefix/auth/login/';
  static String get tokenRefresh => '$prefix/auth/refresh/';
  static String get me => '$prefix/me/';
  static String get consent => '$prefix/consent/';
  static String get checkIn => '$prefix/attendance/checkin/';
  static String get checkOut => '$prefix/attendance/checkout/';
  static String get locationPing => '$prefix/location/ping/';
  static String get locationBatch => '$prefix/location/batch/';
  static String get myAttendance => '$prefix/me/attendance/';
}
