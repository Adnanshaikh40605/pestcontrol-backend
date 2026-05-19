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
    this.scheduleLabel,
    this.scheduleSubLabel,
    this.propertyType,
    this.bhk,
    this.notes,
    this.treatment,
    this.amount,
    this.paymentStatus,
    this.paymentMode,
    this.completionDate,
    this.isPaid = false,
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
  final String? scheduleLabel;
  final String? scheduleSubLabel;
  final String? propertyType;
  final String? bhk;
  final String? notes;
  final String? treatment;
  final String? amount;
  final PaymentStatus? paymentStatus;
  final PaymentMode? paymentMode;
  final String? completionDate;
  final bool isPaid;
}
