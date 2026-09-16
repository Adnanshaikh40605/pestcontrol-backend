import 'package:intl/intl.dart';

/// Booking wall-clock helpers for Asia/Kolkata (IST, UTC+05:30, no DST).
///
/// Never use `DateTime.now().toIso8601String().split('T')` or device-local
/// `.toUtc()` when building the schedule payload — always treat the chosen
/// date/time as IST wall clock.
class BookingTimezone {
  BookingTimezone._();

  static const String id = 'Asia/Kolkata';
  static const Duration offset = Duration(hours: 5, minutes: 30);

  /// Earliest bookable preferred start (inclusive). 12:00 AM–7:59 AM are blocked.
  static const int earliestBookableHour = 8;
  static const int earliestBookableMinute = 0;

  /// Latest bookable service start (inclusive), IST — daytime technician window.
  static const int maxHour = 19;
  static const int maxMinute = 30;

  /// Back-compat aliases for the earliest bookable hour.
  static const int minHour = earliestBookableHour;
  static const int minMinute = earliestBookableMinute;

  /// Current IST wall-clock as a naive local DateTime (isUtc=false values).
  static DateTime now() {
    final utc = DateTime.now().toUtc();
    final ist = utc.add(offset);
    return DateTime(ist.year, ist.month, ist.day, ist.hour, ist.minute, ist.second);
  }

  /// Today's date in IST (midnight wall clock).
  static DateTime today() {
    final n = now();
    return DateTime(n.year, n.month, n.day);
  }

  static bool isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  static bool isBeforeDay(DateTime date, DateTime day) {
    final a = DateTime(date.year, date.month, date.day);
    final b = DateTime(day.year, day.month, day.day);
    return a.isBefore(b);
  }

  static bool isBeforeEarliestBookable(DateTime wallClock) {
    final mins = wallClock.hour * 60 + wallClock.minute;
    return mins < earliestBookableHour * 60 + earliestBookableMinute;
  }

  static bool isBookableTime(int hour, int minute) {
    final mins = hour * 60 + minute;
    return mins >= earliestBookableHour * 60 + earliestBookableMinute;
  }

  /// Coerce night times (00:00–07:59) up to 08:00; leave daytime unchanged.
  static (int hour, int minute) coerceBookableTime(int hour, int minute) {
    if (isBookableTime(hour, minute)) return (hour, minute);
    return (earliestBookableHour, earliestBookableMinute);
  }

  /// Preferred schedule defaults (IST), matching website `getDefaultPreferredSchedule`:
  /// - 12:00 AM–7:59 AM → 8:00 AM same day
  /// - 8:00 AM onward → now + 1 hour, rounded up to 5-minute step
  /// If now+1h lands before 08:00 (late evening), bump to 8:00 AM on that date.
  static DateTime defaultPreferredDateTime([DateTime? nowOverride]) {
    final now = nowOverride ?? BookingTimezone.now();
    if (isBeforeEarliestBookable(now)) {
      return DateTime(now.year, now.month, now.day, earliestBookableHour, earliestBookableMinute);
    }
    var target = now.add(const Duration(hours: 1));
    final rem = target.minute % 5;
    if (rem != 0) {
      target = target.add(Duration(minutes: 5 - rem));
    }
    target = DateTime(target.year, target.month, target.day, target.hour, target.minute);
    if (isBeforeEarliestBookable(target)) {
      return DateTime(
        target.year,
        target.month,
        target.day,
        earliestBookableHour,
        earliestBookableMinute,
      );
    }
    return target;
  }

  /// Default start time for a calendar day (legacy helper).
  /// Future days → 08:00; today uses [defaultPreferredDateTime] rules.
  static (int hour, int minute) defaultTimeFor(DateTime date, {DateTime? nowOverride}) {
    final day = DateTime(date.year, date.month, date.day);
    final n = nowOverride ?? now();
    final todayDay = DateTime(n.year, n.month, n.day);
    if (day.isAfter(todayDay)) {
      return (earliestBookableHour, earliestBookableMinute);
    }
    if (day.isBefore(todayDay)) {
      return (earliestBookableHour, earliestBookableMinute);
    }
    final preferred = defaultPreferredDateTime(n);
    return (preferred.hour, preferred.minute);
  }

  static bool isWithinServiceWindow(int hour, int minute) {
    final mins = hour * 60 + minute;
    final minBound = earliestBookableHour * 60 + earliestBookableMinute;
    final maxBound = maxHour * 60 + maxMinute;
    return mins >= minBound && mins <= maxBound;
  }

  /// True when [date]+[hour]:[minute] is strictly after current IST now
  /// (or any future calendar day).
  static bool isNotInPast(DateTime date, int hour, int minute) {
    final day = DateTime(date.year, date.month, date.day);
    final todayDay = today();
    if (day.isAfter(todayDay)) return true;
    if (day.isBefore(todayDay)) return false;
    final n = now();
    final candidate = DateTime(day.year, day.month, day.day, hour, minute);
    return candidate.isAfter(n);
  }

  static String format12h(int hour24, int minute) {
    final h = hour24 % 24;
    final period = h >= 12 ? 'PM' : 'AM';
    var display = h % 12;
    if (display == 0) display = 12;
    final mm = minute.toString().padLeft(2, '0');
    final hh = display.toString().padLeft(2, '0');
    return '$hh:$mm $period';
  }

  /// ISO-8601 with explicit IST offset — no device-timezone conversion.
  static String toIstIso8601(DateTime date, int hour, int minute) {
    final y = date.year.toString().padLeft(4, '0');
    final m = date.month.toString().padLeft(2, '0');
    final d = date.day.toString().padLeft(2, '0');
    final hh = hour.toString().padLeft(2, '0');
    final mm = minute.toString().padLeft(2, '0');
    return '$y-$m-${d}T$hh:$mm:00+05:30';
  }

  static String bookingDate(DateTime date) {
    final y = date.year.toString().padLeft(4, '0');
    final m = date.month.toString().padLeft(2, '0');
    final d = date.day.toString().padLeft(2, '0');
    return '$y-$m-$d';
  }

  static String bookingTime24(int hour, int minute) {
    final hh = hour.toString().padLeft(2, '0');
    final mm = minute.toString().padLeft(2, '0');
    return '$hh:$mm';
  }

  /// Display a backend datetime string in IST wall clock (not device local).
  static String formatSchedule(String? raw, {String pattern = 'd MMM yyyy, h:mm a'}) {
    if (raw == null || raw.isEmpty) return 'Unscheduled';
    try {
      final parsed = DateTime.parse(raw).toUtc();
      final ist = parsed.add(offset);
      final wall = DateTime(ist.year, ist.month, ist.day, ist.hour, ist.minute);
      return DateFormat(pattern).format(wall);
    } catch (_) {
      return raw;
    }
  }
}
