import 'booking_type.dart';

class Booking {
  const Booking({
    required this.id,
    required this.pestType,
    required this.area,
    required this.dateLabel,
    required this.timeLabel,
    this.customerName,
    this.address,
    this.phone,
    this.bookingType = BookingType.booking,
    this.priority = BookingPriority.standard,
    this.acceptedState,
    this.timeRemaining,
    this.startedAtLabel,
    this.runningForLabel,
    this.scheduleLabel,
    this.scheduleSubLabel,
    this.propertyType,
    this.bhk,
    this.notes,
    this.amount,
    this.paymentStatus,
    this.paymentMode,
    this.completionDate,
    this.isPaid = false,
    this.jobAmount,
    this.yourShareAmount,
    this.companyShareAmount,
    this.visitRevenueAmount,
    this.technicianSharePercent,
    this.companySharePercent,
    this.payoutStatus,
    this.hasRevenuePayout = false,
  });

  final String id;
  final String pestType;
  final String area;
  final String dateLabel;
  final String timeLabel;
  final String? customerName;
  final String? address;
  final String? phone;
  final BookingType bookingType;
  final BookingPriority priority;
  final AcceptedJobState? acceptedState;
  final String? timeRemaining;
  final String? startedAtLabel;
  final String? runningForLabel;
  final String? scheduleLabel;
  final String? scheduleSubLabel;
  final String? propertyType;
  final String? bhk;
  final String? notes;
  final String? amount;
  final PaymentStatus? paymentStatus;
  final PaymentMode? paymentMode;
  final String? completionDate;
  final bool isPaid;

  /// Full job / customer booking amount (not technician money).
  final String? jobAmount;

  /// Technician share for this visit (~40% of visit revenue).
  final String? yourShareAmount;

  /// Company share for this visit (~60%).
  final String? companyShareAmount;

  /// Visit revenue used for 40/60 split (may be less than full package for AMC/Bed Bugs).
  final String? visitRevenueAmount;

  final String? technicianSharePercent;
  final String? companySharePercent;
  final String? payoutStatus;
  final bool hasRevenuePayout;

  String get yourShareLabel {
    final pct = technicianSharePercent?.trim();
    if (pct != null && pct.isNotEmpty && pct != '0' && pct != '0.00') {
      final clean = pct.endsWith('.00') ? pct.substring(0, pct.length - 3) : pct;
      return 'Your share ($clean%)';
    }
    return 'Your share (40%)';
  }

  String get companyShareLabel {
    final pct = companySharePercent?.trim();
    if (pct != null && pct.isNotEmpty && pct != '0' && pct != '0.00') {
      final clean = pct.endsWith('.00') ? pct.substring(0, pct.length - 3) : pct;
      return 'Company share ($clean%)';
    }
    return 'Company share (60%)';
  }
}
