/// Service dates for Pest 99 are booked in India (Asia/Kolkata).
///
/// The partner API sends `schedule_datetime` as an absolute instant
/// (`+05:30` or `Z`). Bucketing with the phone's local calendar moves a
/// morning job onto the previous day in timezones west of India, so it
/// misses both the Today and Tomorrow tabs. India has no daylight saving,
/// so a fixed +05:30 offset matches the CRM and the API date filter.
class ScheduleDay {
  ScheduleDay._();

  static const Duration istOffset = Duration(hours: 5, minutes: 30);

  static final RegExp _explicitZone = RegExp(
    r'(?:z|[+-]\d{2}:?\d{2})$',
    caseSensitive: false,
  );

  /// Absolute instant for an API schedule string.
  ///
  /// Strings with `Z` or an offset are instants. Strings with no zone are
  /// IST wall-clock values, not the phone timezone.
  static DateTime? tryParse(String? raw) {
    if (raw == null) return null;
    final iso = raw.trim();
    if (iso.isEmpty) return null;
    try {
      if (_explicitZone.hasMatch(iso)) {
        return DateTime.parse(iso);
      }
      final parsed = DateTime.parse(iso);
      final wallAsUtc = DateTime.utc(
        parsed.year,
        parsed.month,
        parsed.day,
        parsed.hour,
        parsed.minute,
        parsed.second,
        parsed.millisecond,
        parsed.microsecond,
      );
      return wallAsUtc.subtract(istOffset);
    } catch (_) {
      return null;
    }
  }

  /// Midnight UTC used only as an IST year/month/day key.
  static DateTime istDate(DateTime instant) {
    final shifted = instant.toUtc().add(istOffset);
    return DateTime.utc(shifted.year, shifted.month, shifted.day);
  }

  /// Local [DateTime] whose clock fields are the IST wall time.
  ///
  /// [DateFormat] prints those fields without converting the instant into
  /// the phone timezone.
  static DateTime istWallClock(DateTime instant) {
    final shifted = instant.toUtc().add(istOffset);
    return DateTime(
      shifted.year,
      shifted.month,
      shifted.day,
      shifted.hour,
      shifted.minute,
      shifted.second,
    );
  }

  /// Whole IST calendar days from [now]'s IST date to [instant]'s IST date.
  static int? dayOffset(DateTime instant, DateTime now) {
    return istDate(instant).difference(istDate(now)).inDays;
  }

  /// `today`, `tomorrow`, or `later` (past and beyond tomorrow).
  static String? bucketFor(String? raw, {DateTime? now}) {
    final instant = tryParse(raw);
    if (instant == null) return null;
    final diff = dayOffset(instant, now ?? DateTime.now());
    if (diff == null) return null;
    if (diff == 0) return 'today';
    if (diff == 1) return 'tomorrow';
    return 'later';
  }
}

/// Today / Tomorrow selection for New Bookings.
///
/// A notification hint is applied once per [serial]. Rebuilding while the
/// provider still holds that hint must not undo a tap on the other tab.
class NewBookingDayTab {
  int index = 0;
  int appliedSerial = -1;

  bool select(int next) {
    if (next < 0 || next > 1 || next == index) return false;
    index = next;
    return true;
  }

  /// Returns true when the visible tab changed.
  bool applyHint(int? hint, int serial) {
    if (appliedSerial == serial) return false;
    appliedSerial = serial;
    if (hint == null || hint < 0 || hint > 1) return false;
    if (index == hint) return false;
    index = hint;
    return true;
  }
}
