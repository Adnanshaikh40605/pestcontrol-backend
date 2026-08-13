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
  static String get breakStart => '$prefix/attendance/break/start/';
  static String get breakEnd => '$prefix/attendance/break/end/';
  static String get locationPing => '$prefix/location/ping/';
  static String get locationBatch => '$prefix/location/batch/';
  static String get myAttendance => '$prefix/me/attendance/';
  static String get liveStaff => '$prefix/live/';

  static String get myVisits => '$prefix/visits/mine/';
  static String visitCheckIn(int id) => '$prefix/visits/$id/checkin/';
  static String visitCheckOut(int id) => '$prefix/visits/$id/checkout/';
  static String visitPhoto(int id) => '$prefix/visits/$id/photos/';

  static String get myTasks => '$prefix/tasks/mine/';
  static String taskStatus(int id) => '$prefix/tasks/$id/status/';
  static String taskComments(int id) => '$prefix/tasks/$id/comments/';

  static String get leaveTypes => '$prefix/leave/types/';
  static String get leaveBalance => '$prefix/leave/balance/';
  static String get leaveApply => '$prefix/leave/apply/';
  static String get leaveApplications => '$prefix/leave/applications/';

  static String get expenseCategories => '$prefix/expenses/categories/';
  static String get myExpenses => '$prefix/expenses/mine/';
  static String expenseReceipt(int id) => '$prefix/expenses/$id/receipt/';
}
