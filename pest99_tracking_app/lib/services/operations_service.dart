import '../config/api_config.dart';
import '../core/api_client.dart';

class OperationsService {
  OperationsService(this._api);
  final ApiClient _api;

  Future<List<Map<String, dynamic>>> getMyVisits() async {
    final list = await _api.getList(ApiConfig.myVisits);
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> visitCheckIn(int id, double lat, double lng, {double? accuracy}) {
    return _api.post(ApiConfig.visitCheckIn(id), body: {
      'latitude': lat,
      'longitude': lng,
      'accuracy_m': ?accuracy,
    });
  }

  Future<Map<String, dynamic>> visitCheckOut(int id, double lat, double lng, {String notes = ''}) {
    return _api.post(ApiConfig.visitCheckOut(id), body: {
      'latitude': lat,
      'longitude': lng,
      'notes': notes,
    });
  }

  Future<List<Map<String, dynamic>>> getMyTasks() async {
    final list = await _api.getList(ApiConfig.myTasks);
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> updateTaskStatus(int id, String status, {double? lat, double? lng}) {
    return _api.patch(ApiConfig.taskStatus(id), body: {
      'status': status,
      'latitude': ?lat,
      'longitude': ?lng,
    });
  }

  Future<List<Map<String, dynamic>>> getLeaveTypes() async {
    final list = await _api.getList(ApiConfig.leaveTypes);
    return list.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getLeaveBalance() async {
    final list = await _api.getList(ApiConfig.leaveBalance);
    return list.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getLeaveApplications() async {
    final list = await _api.getList(ApiConfig.leaveApplications);
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> applyLeave({
    required int leaveTypeId,
    required String startDate,
    required String endDate,
    required String reason,
    String halfDay = 'full',
  }) {
    return _api.post(ApiConfig.leaveApply, body: {
      'leave_type_id': leaveTypeId,
      'start_date': startDate,
      'end_date': endDate,
      'reason': reason,
      'half_day': halfDay,
    });
  }

  Future<List<Map<String, dynamic>>> getExpenseCategories() async {
    final list = await _api.getList(ApiConfig.expenseCategories);
    return list.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getMyExpenses() async {
    final list = await _api.getList(ApiConfig.myExpenses);
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> submitExpense({
    required int categoryId,
    required String expenseDate,
    required String amount,
    String description = '',
    bool useGpsDistance = false,
  }) {
    return _api.post(ApiConfig.myExpenses, body: {
      'category_id': categoryId,
      'expense_date': expenseDate,
      'amount': amount,
      'description': description,
      'use_gps_distance': useGpsDistance,
    });
  }

  Future<Map<String, dynamic>> uploadExpenseReceipt(int claimId, String filePath) {
    return _api.postMultipart(ApiConfig.expenseReceipt(claimId), filePath: filePath);
  }

  Future<List<Map<String, dynamic>>> getMyAttendance() async {
    final list = await _api.getList(ApiConfig.myAttendance);
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> startBreak({double? lat, double? lng}) {
    return _api.post(ApiConfig.breakStart, body: {
      'latitude': ?lat,
      'longitude': ?lng,
    });
  }

  Future<Map<String, dynamic>> endBreak() => _api.post(ApiConfig.breakEnd);
}
