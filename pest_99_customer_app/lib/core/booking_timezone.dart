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

  /// Earliest / latest bookable service start (inclusive), IST.
  static const int minHour = 10;
  static const int minMinute = 0;
  static const int maxHour = 19;
  static const int maxMinute = 30;

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

  /// Default start time: next 30-min slot at/after now within service window,
  /// or 10:00 when booking a future day / before window opens.
  static (int hour, int minute) defaultTimeFor(DateTime date) {
    final day = DateTime(date.year, date.month, date.day);
    final todayDay = today();
    if (day.isAfter(todayDay)) {
      return (minHour, minMinute);
    }
    final n = now();
    var hour = n.hour;
    var minute = n.minute;
    // Round up to next 30-minute mark.
    if (minute == 0) {
      // keep
    } else if (minute <= 30) {
      minute = 30;
    } else {
      hour += 1;
      minute = 0;
    }
    if (hour < minHour || (hour == minHour && minute < minMinute)) {
      return (minHour, minMinute);
    }
    if (hour > maxHour || (hour == maxHour && minute > maxMinute)) {
      // Past last slot today — still default to window start; UI will block Continue.
      return (minHour, minMinute);
    }
    return (hour, minute);
  }

  static bool isWithinServiceWindow(int hour, int minute) {
    final mins = hour * 60 + minute;
    final minBound = minHour * 60 + minMinute;
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
