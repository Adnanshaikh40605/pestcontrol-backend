import 'package:intl/intl.dart';

import '../../models/booking.dart' as api;
import '../models/booking.dart';
import '../models/booking_type.dart';

class BookingMapper {
  static Booking fromPartner(api.PartnerBooking b) {
    final schedule = _parseSchedule(b.scheduleDatetime);
    return Booking(
      id: '${b.id}',
      pestType: b.serviceType,
      area: b.locationDisplay ?? b.clientAddress ?? '—',
      dateLabel: schedule.dateLabel,
      timeLabel: b.timeSlot ?? schedule.timeLabel,
      customerName: b.clientName,
      address: b.locationDisplay ?? b.clientAddress,
      phone: b.canViewClientPhone ? b.clientMobile : null,
      bookingType: _bookingType(b.bookingType),
      priority: (b.bookingTag?.toLowerCase().contains('high') ?? false)
          ? BookingPriority.high
          : BookingPriority.standard,
      acceptedState: _acceptedState(b),
      scheduleLabel: schedule.dateLabel,
      scheduleSubLabel: b.timeSlot ?? schedule.timeLabel,
      propertyType: b.serviceCategory,
      notes: b.notes,
      amount: b.priceDisplay ?? b.price,
      paymentStatus: _paymentStatus(b.paymentStatus),
      paymentMode: _paymentMode(b.paymentMode),
      isPaid: b.paymentStatus?.toLowerCase() == 'paid',
    );
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

  static BookingType _bookingType(String? raw) {
    final v = (raw ?? '').toLowerCase();
    if (v.contains('service call')) return BookingType.serviceCall;
    if (v.contains('complaint')) return BookingType.complaintCall;
    if (v.contains('follow')) return BookingType.followUp;
    if (v.contains('amc')) return BookingType.amcVisit;
    return BookingType.booking;
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
      return const _ScheduleParts(dateLabel: '—', timeLabel: '—');
    }
    try {
      final dt = DateTime.parse(iso).toLocal();
      return _ScheduleParts(
        dateLabel: DateFormat('EEE, d MMM').format(dt),
        timeLabel: DateFormat('h:mm a').format(dt),
      );
    } catch (_) {
      return _ScheduleParts(dateLabel: iso, timeLabel: '—');
    }
  }
}

class _ScheduleParts {
  const _ScheduleParts({required this.dateLabel, required this.timeLabel});
  final String dateLabel;
  final String timeLabel;
}
