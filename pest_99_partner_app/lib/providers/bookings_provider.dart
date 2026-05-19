import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/api_exception.dart';
import '../core/network_connectivity.dart';
import '../models/booking.dart';
import '../models/booking_action_result.dart';
import '../services/booking_service.dart';

class BookingsProvider extends ChangeNotifier {
  BookingsProvider(this._service, {NetworkConnectivity? connectivity})
      : _connectivity = connectivity ?? NetworkConnectivity();

  final BookingService _service;
  final NetworkConnectivity _connectivity;

  BookingCounts counts = BookingCounts(available: 0, accepted: 0, completed: 0);
  List<PartnerBooking> available = [];
  List<PartnerBooking> accepted = [];
  List<PartnerBooking> completed = [];

  bool loading = false;
  String? error;

  final Map<int, String> _processingLabels = {};
  final Set<int> _processingIds = {};

  bool isProcessing(int id) => _processingIds.contains(id);

  String? processingLabel(int id) => _processingLabels[id];

  bool get isGlobalBusy => _processingIds.isNotEmpty;

  Future<void> refreshAll() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final results = await Future.wait([
        _service.getCounts(),
        _service.getAvailable(),
        _service.getAccepted(),
        _service.getCompleted(),
      ]);
      counts = results[0] as BookingCounts;
      available = results[1] as List<PartnerBooking>;
      accepted = results[2] as List<PartnerBooking>;
      completed = results[3] as List<PartnerBooking>;
    } on ApiException catch (e) {
      error = e.message;
    } catch (_) {
      error = 'Could not load bookings.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<BookingActionResult> accept(int id) => _runAction(
        id,
        initialLabel: 'Accepting…',
        action: () async {
          await _service.accept(id);
          await refreshAll();
          return BookingActionResult.ok(
            message: 'Job accepted',
            navigateToAccepted: true,
          );
        },
      );

  Future<BookingActionResult> reject(int id) => _runAction(
        id,
        initialLabel: 'Rejecting…',
        action: () async {
          await _service.reject(id);
          available = available.where((b) => b.id != id).toList();
          counts = BookingCounts(
            available: (counts.available - 1).clamp(0, 999999),
            accepted: counts.accepted,
            completed: counts.completed,
          );
          notifyListeners();
          unawaited(refreshAll());
          return BookingActionResult.ok(message: 'Booking rejected');
        },
      );

  Future<BookingActionResult> startJob(int id, String selfiePath) => _runAction(
        id,
        initialLabel: 'Uploading selfie…',
        onProgress: (label) => _setProcessing(id, label),
        action: () async {
          _setProcessing(id, 'Uploading selfie…');
          await _service.startWithSelfie(id, selfiePath);
          _setProcessing(id, 'Starting service…');
          final updated = await _service.getDetail(id);
          _replaceInAccepted(updated);
          notifyListeners();
          unawaited(_syncCounts());
          return BookingActionResult.ok(message: 'Job started');
        },
      );

  Future<BookingActionResult> completeJob(int id, String paymentMode) => _runAction(
        id,
        initialLabel: 'Ending service…',
        onProgress: (label) => _setProcessing(id, label),
        action: () async {
          _setProcessing(id, 'Ending service…');
          await _service.complete(id, paymentMode);
          _setProcessing(id, 'Saving payment…');
          final updated = await _service.getDetail(id);
          accepted = accepted.where((b) => b.id != id).toList();
          completed = [updated, ...completed.where((b) => b.id != id)];
          notifyListeners();
          unawaited(_syncCounts());
          return BookingActionResult.ok(
            message: 'Service completed',
            navigateToCompleted: true,
          );
        },
      );

  void _replaceInAccepted(PartnerBooking updated) {
    final idx = accepted.indexWhere((b) => b.id == updated.id);
    if (idx >= 0) {
      final next = List<PartnerBooking>.from(accepted);
      next[idx] = updated;
      accepted = next;
    } else {
      accepted = [...accepted, updated];
    }
  }

  Future<void> _syncCounts() async {
    try {
      counts = await _service.getCounts();
      notifyListeners();
    } catch (_) {}
  }

  Future<BookingActionResult> _runAction(
    int id, {
    required String initialLabel,
    required Future<BookingActionResult> Function() action,
    void Function(String label)? onProgress,
  }) async {
    if (_processingIds.contains(id)) {
      return BookingActionResult.fail('Please wait…');
    }

    if (!await _connectivity.hasConnection()) {
      return BookingActionResult.fail('No internet connection');
    }

    _setProcessing(id, initialLabel);
    try {
      return await action();
    } on ApiException catch (e) {
      error = e.message;
      notifyListeners();
      final msg = e.statusCode == 408
          ? 'Network slow. Please try again.'
          : e.message;
      return BookingActionResult.fail(msg);
    } catch (_) {
      return BookingActionResult.fail('Something went wrong. Please try again.');
    } finally {
      _clearProcessing(id);
    }
  }

  void _setProcessing(int id, String label) {
    _processingIds.add(id);
    _processingLabels[id] = label;
    notifyListeners();
    // onProgress callback unused in _runAction but kept for future multi-step
  }

  void _clearProcessing(int id) {
    _processingIds.remove(id);
    _processingLabels.remove(id);
    notifyListeners();
  }
}
