import 'package:intl/intl.dart';

import '../../models/booking.dart' as api;
import '../models/booking.dart';
import '../models/booking_type.dart';

class BookingMapper {
  static Booking fromPartner(api.PartnerBooking b) {
    final schedule = _parseSchedule(b.scheduleDatetime);
    final started = _startedLabels(b.startedAt);
    final amount = b.totalBookingAmount ?? b.priceDisplay ?? b.price;
    return Booking(
      id: '${b.id}',
      pestType: b.serviceType,
      // Short locality + city for New Bookings cards (never full address).
      area: shortAreaLabel(b),
      dateLabel: schedule.dateLabel,
      timeLabel: b.timeSlot ?? schedule.timeLabel,
      customerName: b.clientName,
      // Full location kept for Accepted / Details flows.
      address: b.locationDisplay ?? b.clientAddress,
      phone: b.canViewClientPhone ? b.clientMobile : null,
      bookingType: _bookingType(b.bookingType, b.planLabel, b.serviceCategory),
      planLabel: b.planLabel ?? _planFromCategory(b.serviceCategory, b.bookingType),
      dayBucket: schedule.dayBucket,
      priority: (b.bookingTag?.toLowerCase().contains('high') ?? false)
          ? BookingPriority.high
          : BookingPriority.standard,
      acceptedState: _acceptedState(b),
      startedAtLabel: started.$1,
      runningForLabel: started.$2,
      scheduleLabel: schedule.dateLabel,
      scheduleSubLabel: b.timeSlot ?? schedule.timeLabel,
      propertyType: b.serviceCategory,
      notes: b.notes,
      amount: amount,
      paymentStatus: _paymentStatus(b.paymentStatus),
      paymentMode: _paymentMode(b.paymentMode),
      isPaid: (b.paymentStatus ?? '').toLowerCase() == 'paid',
      jobAmount: amount,
      yourShareAmount: b.visitPayoutAmount,
      companyShareAmount: b.companyShareAmount,
      visitRevenueAmount: b.visitRevenueAmount,
      technicianSharePercent: b.technicianSharePercent,
      companySharePercent: b.companySharePercent,
      payoutStatus: b.payoutStatus,
      hasRevenuePayout: b.hasRevenuePayout,
    );
  }

  /// Locality + city only, e.g. "Kondhwa, Pune". Never flat/building/PIN.
  static String shortAreaLabel(api.PartnerBooking b) {
    final locality = (b.localityName ?? '').trim();
    final city = (b.cityName ?? '').trim();
    if (locality.isNotEmpty && city.isNotEmpty) {
      if (locality.toLowerCase() == city.toLowerCase()) return city;
      return '$locality, $city';
    }
    if (locality.isNotEmpty) return locality;
    if (city.isNotEmpty) return city;

    // Fallback: try to peel a locality,city from a long address string.
    final raw = (b.locationDisplay ?? b.clientAddress ?? '').trim();
    if (raw.isEmpty) return '—';
    return _guessShortArea(raw);
  }

  static String _guessShortArea(String raw) {
    final parts = raw
        .split(',')
        .map((p) => p.trim())
        .where((p) => p.isNotEmpty)
        .toList();
    if (parts.isEmpty) return '—';

    // Drop trailing country / PIN / state-ish tokens
    final filtered = parts.where((p) {
      final lower = p.toLowerCase();
      if (lower == 'india') return false;
      if (RegExp(r'^\d{6}$').hasMatch(p.replaceAll(' ', ''))) return false;
      if (lower.contains('maharashtra') || lower.contains('maharastra')) return false;
      // Flat / building noise
      if (RegExp(r'^(flat|apt|apartment|bldg|building|wing|floor|society)\b', caseSensitive: false)
          .hasMatch(lower)) {
        return false;
      }
      if (RegExp(r'^[A-Za-z]?\d+[-/]').hasMatch(p)) return false; // B8-503 style
      return true;
    }).toList();

    if (filtered.isEmpty) return parts.length >= 2 ? '${parts[parts.length - 2]}, ${parts.last}' : parts.last;
    if (filtered.length == 1) return filtered.first;
    // Prefer last two remaining tokens: locality, city
    return '${filtered[filtered.length - 2]}, ${filtered.last}';
  }

  static AcceptedJobState? _acceptedState(api.PartnerBooking b) {
    switch (b.partnerStatus) {
      case 'in_service':
        return AcceptedJobState.inService;
      case 'accepted':
        return AcceptedJobState.pending;
      case 'completed':
        return AcceptedJobState.completed;
      default:
        if (b.canCompleteJob) return AcceptedJobState.inService;
        if (b.canStartJob) return AcceptedJobState.pending;
        return null;
    }
  }

  static BookingType _bookingType(String? raw, String? planLabel, String? category) {
    final plan = (planLabel ?? '').toLowerCase();
    if (plan.contains('amc')) return BookingType.amcVisit;
    if (plan.contains('one')) return BookingType.oneTime;
    final v = (raw ?? '').toLowerCase();
    if (v.contains('service call')) return BookingType.serviceCall;
    if (v.contains('complaint')) return BookingType.complaintCall;
    if (v.contains('follow')) return BookingType.followUp;
    if (v.contains('amc')) return BookingType.amcVisit;
    final cat = (category ?? '').toLowerCase();
    if (cat.contains('amc')) return BookingType.amcVisit;
    return BookingType.oneTime;
  }

  static String _planFromCategory(String? category, String? bookingType) {
    final cat = (category ?? '').toLowerCase();
    final bt = (bookingType ?? '').toLowerCase();
    if (cat.contains('amc') || bt.contains('amc')) return 'AMC';
    return 'One-Time';
  }

  static PaymentStatus? _paymentStatus(String? raw) {
    final v = (raw ?? '').toLowerCase();
    if (v == 'paid') return PaymentStatus.paid;
    if (v == 'pending') return PaymentStatus.pending;
    if (v.isNotEmpty) return PaymentStatus.unpaid;
    return null;
  }

  static PaymentMode? _paymentMode(String? raw) {
    final v = (raw ?? '').toLowerCase();
    if (v.contains('online')) return PaymentMode.online;
    if (v.contains('cash')) return PaymentMode.cash;
    return null;
  }

  static _ScheduleParts _parseSchedule(String? iso) {
    if (iso == null || iso.isEmpty) {
      return const _ScheduleParts(dateLabel: '—', timeLabel: '—', dayBucket: null);
    }
    try {
      final dt = DateTime.parse(iso).toLocal();
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final day = DateTime(dt.year, dt.month, dt.day);
      final diff = day.difference(today).inDays;
      String? bucket;
      String dateLabel;
      if (diff == 0) {
        bucket = 'today';
        dateLabel = 'Today';
      } else if (diff == 1) {
        bucket = 'tomorrow';
        dateLabel = 'Tomorrow';
      } else {
        bucket = 'later';
        dateLabel = DateFormat('EEE, d MMM').format(dt);
      }
      return _ScheduleParts(
        dateLabel: dateLabel,
        timeLabel: DateFormat('h:mm a').format(dt),
        dayBucket: bucket,
      );
    } catch (_) {
      return _ScheduleParts(dateLabel: iso, timeLabel: '—', dayBucket: null);
    }
  }

  /// Returns (startedAtLabel, runningForLabel).
  static (String?, String?) _startedLabels(String? iso) {
    if (iso == null || iso.isEmpty) {
      return ('Service in progress', null);
    }
    try {
      final started = DateTime.parse(iso).toLocal();
      final startedLabel = 'Started at ${DateFormat('h:mm a').format(started)}';
      final mins = DateTime.now().difference(started).inMinutes;
      if (mins < 1) return (startedLabel, 'Just started');
      if (mins < 60) return (startedLabel, 'Running for $mins mins');
      final hours = mins ~/ 60;
      final rem = mins % 60;
      final running = rem == 0
          ? 'Running for ${hours}h'
          : 'Running for ${hours}h ${rem}m';
      return (startedLabel, running);
    } catch (_) {
      return ('Service in progress', null);
    }
  }
}

class _ScheduleParts {
  const _ScheduleParts({
    required this.dateLabel,
    required this.timeLabel,
    this.dayBucket,
  });

  final String dateLabel;
  final String timeLabel;
  final String? dayBucket;
}
