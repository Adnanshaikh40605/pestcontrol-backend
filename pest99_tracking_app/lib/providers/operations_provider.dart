import 'package:flutter/foundation.dart';

import '../services/location_service.dart';
import '../services/operations_service.dart';

class OperationsProvider extends ChangeNotifier {
  OperationsProvider(this._ops, this._location);

  final OperationsService _ops;
  final LocationService _location;

  List<Map<String, dynamic>> visits = [];
  List<Map<String, dynamic>> tasks = [];
  List<Map<String, dynamic>> leaveBalances = [];
  List<Map<String, dynamic>> leaveApplications = [];
  List<Map<String, dynamic>> leaveTypes = [];
  List<Map<String, dynamic>> expenseCategories = [];
  List<Map<String, dynamic>> expenses = [];
  List<Map<String, dynamic>> attendance = [];

  bool loading = false;
  String? error;

  Future<void> loadVisits() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      visits = await _ops.getMyVisits();
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<bool> checkInVisit(int id) async {
    try {
      final pos = await _location.getCurrentPosition();
      await _ops.visitCheckIn(id, pos.latitude, pos.longitude, accuracy: pos.accuracy);
      await loadVisits();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> checkOutVisit(int id, {String notes = ''}) async {
    try {
      final pos = await _location.getCurrentPosition();
      await _ops.visitCheckOut(id, pos.latitude, pos.longitude, notes: notes);
      await loadVisits();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> loadTasks() async {
    loading = true;
    notifyListeners();
    try {
      tasks = await _ops.getMyTasks();
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<bool> completeTask(int id) async {
    try {
      final pos = await _location.getCurrentPosition();
      await _ops.updateTaskStatus(id, 'completed', lat: pos.latitude, lng: pos.longitude);
      await loadTasks();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> loadLeave() async {
    loading = true;
    notifyListeners();
    try {
      leaveTypes = await _ops.getLeaveTypes();
      leaveBalances = await _ops.getLeaveBalance();
      leaveApplications = await _ops.getLeaveApplications();
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<bool> applyLeave({
    required int leaveTypeId,
    required String startDate,
    required String endDate,
    required String reason,
  }) async {
    try {
      await _ops.applyLeave(
        leaveTypeId: leaveTypeId,
        startDate: startDate,
        endDate: endDate,
        reason: reason,
      );
      await loadLeave();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> loadExpenses() async {
    loading = true;
    notifyListeners();
    try {
      expenseCategories = await _ops.getExpenseCategories();
      expenses = await _ops.getMyExpenses();
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<bool> submitExpense({
    required int categoryId,
    required String date,
    required String amount,
    String description = '',
    bool useGps = false,
  }) async {
    try {
      await _ops.submitExpense(
        categoryId: categoryId,
        expenseDate: date,
        amount: amount,
        description: description,
        useGpsDistance: useGps,
      );
      await loadExpenses();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> loadAttendance() async {
    loading = true;
    notifyListeners();
    try {
      attendance = await _ops.getMyAttendance();
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> uploadReceipt(int claimId, String filePath) async {
    await _ops.uploadExpenseReceipt(claimId, filePath);
    await loadExpenses();
  }

  Future<bool> startBreak() async {
    try {
      await _ops.startBreak();
      error = null;
      notifyListeners();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> endBreak() async {
    try {
      await _ops.endBreak();
      error = null;
      notifyListeners();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }
}
