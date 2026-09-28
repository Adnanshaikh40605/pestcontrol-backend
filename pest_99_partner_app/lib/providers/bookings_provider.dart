import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/api_exception.dart';
import '../core/mappers/booking_mapper.dart';
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

  /// Marked on leave by the office. Blocks new work just like suspension.
  bool isOnLeave = false;
  String? presenceStatus;
  String suspendReason = '';
  String suspendMessage = '';

  /// Either on leave or suspended — no new bookings are being sent.
  bool get isUnavailable => isSuspended || isOnLeave;

  /// True for secondary technicians: the office assigns their jobs, so the
  /// New Bookings tab is empty by design rather than because of an error.
  bool manualAssignOnly = false;
  String manualAssignMessage = '';

  final Map<int, String> _processingLabels = {};
  final Set<int> _processingIds = {};

  /// Jobs opened from a push that the list endpoint omitted. Re-applied after
  /// refresh so a 45s sync cannot make the tapped booking disappear again.
  final Map<int, PartnerBooking> _pinnedAvailable = {};

  /// 0 = Today, 1 = Tomorrow. Set when a notification booking is revealed.
  ///
  /// Null means the job is not on those tabs (Later, or the date is unknown).
  int? notificationDayTab;

  /// Bumps every time a notification asks the list to focus a booking.
  /// The screen applies each serial once so a rebuild cannot undo a tab tap.
  int notificationHintSerial = 0;

  /// Card to scroll into view. Set for Later jobs so they are not left under
  /// an empty Today tab.
  int? focusBookingId;

  /// True when the tapped booking is already accepted and belongs on that tab.
  bool notificationOpensAccepted = false;

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
      _mergePinnedAvailable();
      isSuspended = availableResult.isSuspended;
      isOnLeave = availableResult.isOnLeave;
      presenceStatus = availableResult.presenceStatus;
      suspendReason = availableResult.suspendReason;
      suspendMessage = availableResult.message;
      manualAssignOnly = availableResult.manualAssignOnly;
      manualAssignMessage =
          availableResult.manualAssignOnly ? availableResult.message : '';
      accepted = results[2] as List<PartnerBooking>;
      completed = results[3] as List<PartnerBooking>;
      if (!showGlobalLoader) error = null;
    } on ApiException catch (e) {
      if (e.isSessionExpired) {
        // ApiClient already cleared tokens + SessionCoordinator will route to Login.
        error = null;
      } else if (showGlobalLoader || available.isEmpty) {
        error = userErrorMessage(e, fallback: 'Could not load bookings.');
      }
    } catch (e) {
      if (kDebugMode) debugPrint('[Bookings] refresh error: $e');
      if (isPartnerSessionExpiredError(e)) {
        error = null;
      } else if (showGlobalLoader || available.isEmpty) {
        error = userErrorMessage(e, fallback: 'Could not load bookings.');
      }
    } finally {
      if (showGlobalLoader) loading = false;
      notifyListeners();
    }
  }

  /// Drop the hint after the New Bookings screen has applied it.
  ///
  /// A newer reveal that already changed the tab is left alone.
  void clearNotificationDayTab([int? applied]) {
    if (applied != null && notificationDayTab != applied) return;
    notificationDayTab = null;
  }

  /// Point Today/Tomorrow or the Later list at a notification before the
  /// detail route opens. The payload schedule is enough; the API refresh
  /// confirms it afterwards.
  void showNotificationBooking({
    required int id,
    int? dayTab,
    required bool scrollToCard,
  }) {
    notificationDayTab = dayTab;
    notificationHintSerial++;
    focusBookingId = scrollToCard ? id : null;
    notifyListeners();
  }

  bool takeNotificationOpensAccepted() {
    final open = notificationOpensAccepted;
    notificationOpensAccepted = false;
    return open;
  }

  /// Load lists, then make [id] visible on New Bookings or Accepted.
  ///
  /// A push is sent for every new booking, but the available list used to
  /// drop anything outside today/tomorrow. Tapping that notification refreshed
  /// into an empty Today and Tomorrow tab. This fetches the booking by id when
  /// the list omits it and points the day tabs at its IST date.
  Future<void> revealNotificationBooking(int id) async {
    await refreshListsLight(force: true);
    var booking = _findBooking(id);
    if (booking == null) {
      await refreshListsLight(force: true);
      booking = _findBooking(id);
    }
    if (booking == null) {
      try {
        booking = await _service.getDetail(id);
      } catch (e) {
        if (kDebugMode) {
          debugPrint('[Bookings] notification booking #$id not loaded: $e');
        }
        notificationOpensAccepted = false;
        return;
      }
    }

    final status = (booking.partnerStatus ?? '').toLowerCase();
    final jobStatus = (booking.status ?? '').toLowerCase();
    final accepted = status == 'accepted' || status == 'in_service';
    final closed = status == 'completed' ||
        status == 'rejected' ||
        jobStatus == 'cancelled' ||
        jobStatus == 'done';

    notificationOpensAccepted = accepted && !closed;
    if (closed) {
      _pinnedAvailable.remove(id);
      focusBookingId = null;
      notifyListeners();
      return;
    }

    if (accepted) {
      _pinnedAvailable.remove(id);
      if (!this.accepted.any((b) => b.id == id)) {
        this.accepted = [booking, ...this.accepted];
      }
      notificationDayTab = null;
      focusBookingId = null;
    } else {
      _pinnedAvailable[id] = booking;
      if (!available.any((b) => b.id == id)) {
        available = [booking, ...available];
      }
      final dayTab = _dayTabFor(booking);
      notificationDayTab = dayTab;
      notificationHintSerial++;
      focusBookingId = dayTab == null ? id : null;
    }
    notifyListeners();
  }

  PartnerBooking? _findBooking(int id) {
    for (final list in [available, accepted, completed]) {
      for (final booking in list) {
        if (booking.id == id) return booking;
      }
    }
    return null;
  }

  int? _dayTabFor(PartnerBooking booking) {
    switch (BookingMapper.fromPartner(booking).dayBucket) {
      case 'today':
        return 0;
      case 'tomorrow':
        return 1;
      default:
        return null;
    }
  }

  void _mergePinnedAvailable() {
    if (_pinnedAvailable.isEmpty) return;
    final visible = {for (final booking in available) booking.id};
    final extras = <PartnerBooking>[];
    for (final entry in _pinnedAvailable.entries) {
      if (accepted.any((b) => b.id == entry.key)) continue;
      if (completed.any((b) => b.id == entry.key)) continue;
      if (!visible.contains(entry.key)) extras.add(entry.value);
    }
    if (extras.isEmpty) return;
    available = _dedupeById([...extras, ...available]);
  }

  void removeFromAvailable(int id) {
    _pinnedAvailable.remove(id);
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
    _pinnedAvailable.remove(booking.id);
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
