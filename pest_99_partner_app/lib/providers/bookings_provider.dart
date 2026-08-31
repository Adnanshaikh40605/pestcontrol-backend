import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/api_exception.dart';
import '../core/network_connectivity.dart';
import '../core/user_error.dart';
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
  bool isSuspended = false;
  String suspendReason = '';
  String suspendMessage = '';

  final Map<int, String> _processingLabels = {};
  final Set<int> _processingIds = {};

  bool isProcessing(int id) => _processingIds.contains(id);

  String? processingLabel(int id) => _processingLabels[id];

  bool get isGlobalBusy => _processingIds.isNotEmpty;

  static List<PartnerBooking> _dedupeById(List<PartnerBooking> rows) {
    final seen = <int>{};
    final out = <PartnerBooking>[];
    for (final row in rows) {
      if (seen.add(row.id)) out.add(row);
    }
    return out;
  }

  static const _minRefreshGap = Duration(seconds: 8);

  Future<void>? _refreshInFlight;
  DateTime? _lastRefreshAt;

  /// Full load with global spinner (first open / pull-to-refresh).
  Future<void> refreshAll({bool force = false}) async {
    await _refreshLists(showGlobalLoader: true, force: force);
  }

  /// Background sync — no full-screen loader.
  Future<void> refreshListsLight({bool force = false}) async {
    await _refreshLists(showGlobalLoader: false, force: force);
  }

  Future<void> _refreshLists({
    required bool showGlobalLoader,
    bool force = false,
  }) async {
    if (_refreshInFlight != null) {
      return _refreshInFlight;
    }
    final now = DateTime.now();
    if (!force &&
        _lastRefreshAt != null &&
        now.difference(_lastRefreshAt!) < _minRefreshGap) {
      return;
    }

    _refreshInFlight = _refreshInternal(showGlobalLoader);
    try {
      await _refreshInFlight;
    } finally {
      _refreshInFlight = null;
      _lastRefreshAt = DateTime.now();
    }
  }

  Future<void> _refreshInternal(bool showGlobalLoader) async {
    if (showGlobalLoader) {
      loading = true;
      error = null;
      notifyListeners();
    }

    if (!await _connectivity.hasConnection()) {
      if (showGlobalLoader || available.isEmpty) {
        error = 'No internet connection';
      }
      if (showGlobalLoader) loading = false;
      notifyListeners();
      return;
    }

    try {
      final results = await Future.wait([
        _service.getCounts(),
        _service.getAvailable(),
        _service.getAccepted(),
        _service.getCompleted(),
      ]);
      counts = results[0] as BookingCounts;
      final availableResult = results[1] as AvailableBookingsResult;
      available = _dedupeById(availableResult.bookings);
      isSuspended = availableResult.isSuspended;
      suspendReason = availableResult.suspendReason;
      suspendMessage = availableResult.message;
      accepted = results[2] as List<PartnerBooking>;
      completed = results[3] as List<PartnerBooking>;
      if (!showGlobalLoader) error = null;
    } on ApiException catch (e) {
      if (showGlobalLoader || available.isEmpty) {
        error = userErrorMessage(e, fallback: 'Could not load bookings.');
      }
    } catch (e) {
      if (kDebugMode) debugPrint('[Bookings] refresh error: $e');
      if (showGlobalLoader || available.isEmpty) {
        error = userErrorMessage(e, fallback: 'Could not load bookings.');
      }
    } finally {
      if (showGlobalLoader) loading = false;
      notifyListeners();
    }
  }

  void removeFromAvailable(int id) {
    final next = available.where((b) => b.id != id).toList();
    if (next.length == available.length) return;
    available = next;
    counts = BookingCounts(
      available: (counts.available - 1).clamp(0, 999999),
      accepted: counts.accepted,
      completed: counts.completed,
    );
    notifyListeners();
  }

  void removeFromAccepted(int id) {
    final next = accepted.where((b) => b.id != id).toList();
    if (next.length == accepted.length) return;
    accepted = next;
    counts = BookingCounts(
      available: counts.available,
      accepted: accepted.length,
      completed: counts.completed,
    );
    notifyListeners();
  }

  void applyAcceptedBooking(PartnerBooking booking) {
    available = available.where((b) => b.id != booking.id).toList();
    final idx = accepted.indexWhere((b) => b.id == booking.id);
    if (idx >= 0) {
      final next = List<PartnerBooking>.from(accepted);
      next[idx] = booking;
      accepted = next;
    } else {
      accepted = [booking, ...accepted];
    }
    counts = BookingCounts(
      available: available.length,
      accepted: accepted.length,
      completed: counts.completed,
    );
    notifyListeners();
  }

  Future<BookingActionResult> accept(int id) => _runAction(
        id,
        initialLabel: 'Accepting…',
        action: () async {
          try {
            await _service.accept(id);
          } on ApiException catch (e) {
            if (_handleStaleBookingError(id, e)) {
              return BookingActionResult.fail(_staleMessage(e));
            }
            rethrow;
          }
          try {
            final detail = await _service.getDetail(id);
            applyAcceptedBooking(detail);
          } catch (_) {
            // Accept already succeeded — keep optimistic list update via refresh.
            removeFromAvailable(id);
            unawaited(refreshListsLight(force: true));
          }
          unawaited(_syncCounts());
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
          try {
            await _service.reject(id);
          } on ApiException catch (e) {
            if (_handleStaleBookingError(id, e)) {
              return BookingActionResult.fail(_staleMessage(e));
            }
            rethrow;
          }
          removeFromAvailable(id);
          unawaited(_syncCounts());
          return BookingActionResult.ok(message: 'Booking rejected');
        },
      );

  Future<BookingActionResult> startJob(int id, String selfiePath) => _runAction(
        id,
        initialLabel: 'Uploading selfie…',
        action: () async {
          try {
            await _service.startWithSelfie(id, selfiePath);
          } on ApiException catch (e) {
            if (_handleStaleBookingError(id, e)) {
              return BookingActionResult.fail(_staleMessage(e));
            }
            rethrow;
          }
          try {
            final updated = await _service.getDetail(id);
            _replaceInAccepted(updated);
          } catch (_) {
            unawaited(refreshListsLight(force: true));
          }
          notifyListeners();
          unawaited(_syncCounts());
          return BookingActionResult.ok(message: 'Job started');
        },
      );

  Future<BookingActionResult> completeJob(int id, String paymentMode) => _runAction(
        id,
        initialLabel: 'Ending service…',
        action: () async {
          try {
            await _service.complete(id, paymentMode);
          } on ApiException catch (e) {
            if (_handleStaleBookingError(id, e)) {
              return BookingActionResult.fail(_staleMessage(e));
            }
            rethrow;
          }
          PartnerBooking? updated;
          try {
            updated = await _service.getDetail(id);
          } catch (_) {
            // Complete already succeeded — don't fail UX on detail fetch.
          }
          accepted = accepted.where((b) => b.id != id).toList();
          if (updated != null) {
            completed = [updated, ...completed.where((b) => b.id != id)];
          }
          counts = BookingCounts(
            available: counts.available,
            accepted: accepted.length,
            completed: updated != null
                ? completed.length
                : (counts.completed + 1).clamp(0, 999999),
          );
          notifyListeners();
          unawaited(_syncCounts());
          return BookingActionResult.ok(
            message: 'Service completed',
            navigateToCompleted: true,
          );
        },
      );

  /// Remove stale booking from lists when CRM already cancelled / removed.
  bool _handleStaleBookingError(int id, ApiException e) {
    final cancelled = e.code == 'cancelled_in_crm';
    final gone = e.statusCode == 404;
    final taken = e.statusCode == 409 && e.code == 'already_accepted';
    if (taken) {
      removeFromAvailable(id);
      unawaited(_syncCounts());
      return true;
    }
    if (cancelled || gone) {
      removeFromAvailable(id);
      removeFromAccepted(id);
      unawaited(_syncCounts());
      return true;
    }
    return false;
  }

  String _staleMessage(ApiException e) =>
      userErrorMessage(e, fallback: 'This booking is no longer available.');

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
    } catch (e) {
      if (kDebugMode) debugPrint('[Bookings] syncCounts: $e');
    }
  }

  Future<BookingActionResult> _runAction(
    int id, {
    required String initialLabel,
    required Future<BookingActionResult> Function() action,
  }) async {
    if (_processingIds.contains(id)) {
      return BookingActionResult.fail('Please wait…');
    }

    if (!await _connectivity.hasConnection()) {
      return BookingActionResult.fail('No internet connection. Check your connection and try again.');
    }

    _setProcessing(id, initialLabel);
    try {
      return await action();
    } on ApiException catch (e) {
      return BookingActionResult.fail(userErrorMessage(e));
    } catch (e) {
      if (kDebugMode) debugPrint('[Bookings] action #$id error: $e');
      return BookingActionResult.fail(userErrorMessage(e));
    } finally {
      _clearProcessing(id);
    }
  }

  void _setProcessing(int id, String label) {
    _processingIds.add(id);
    _processingLabels[id] = label;
    notifyListeners();
  }

  void _clearProcessing(int id) {
    _processingIds.remove(id);
    _processingLabels.remove(id);
    notifyListeners();
  }
}
