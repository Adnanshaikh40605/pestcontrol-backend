import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_partner_app/models/booking.dart';
import 'package:pest_99_partner_app/shared/widgets/call_sections.dart';

PartnerBooking _job({
  required int id,
  String? bookingType,
  String? bookingTag,
  String? planLabel,
  String? serviceCategory,
  bool serviceFlag = false,
  bool complaintFlag = false,
}) {
  return PartnerBooking(
    id: id,
    serviceType: 'General Pest',
    bookingType: bookingType,
    bookingTag: bookingTag,
    planLabel: planLabel,
    serviceCategory: serviceCategory,
    isServiceCallFlag: serviceFlag,
    isComplaintCallFlag: complaintFlag,
  );
}

void main() {
  test('service calls and complaint calls are separate from AMC visits', () {
    final split = CallKindSplit.from([
      _job(id: 1, bookingType: 'Service Call', bookingTag: 'SERVICE CALL'),
      _job(id: 2, complaintFlag: true, bookingType: 'Complaint Call'),
      _job(
        id: 3,
        bookingType: 'AMC Followup',
        bookingTag: 'AMC VISIT',
        planLabel: 'AMC',
        serviceCategory: 'amc',
        serviceFlag: true,
      ),
      _job(id: 4, bookingType: 'New Booking', bookingTag: 'STANDARD'),
    ]);

    expect(split.serviceCalls.map((b) => b.id), [1]);
    expect(split.complaintCalls.map((b) => b.id), [2]);
    expect(split.other.map((b) => b.id), [3, 4]);
  });
}
