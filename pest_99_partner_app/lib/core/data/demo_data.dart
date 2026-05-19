import '../models/booking.dart';
import '../models/booking_type.dart';

abstract final class DemoData {
  static const technicianName = 'Alex Rivera';
  static const technicianPhone = '+1 (555) 123-4567';
  static const technicianRole = 'Senior Technician';

  static final List<Booking> availableBookings = [
    const Booking(
      id: 'BKG-8472',
      pestType: 'Termite Control',
      area: '124 Maple Street, Northside Area',
      dateLabel: 'Today, Oct 24',
      timeLabel: '14:00 - 16:00',
      priority: BookingPriority.high,
    ),
    const Booking(
      id: 'BKG-8475',
      pestType: 'Cockroach Treatment',
      area: 'Apt 4B, Sunset Towers, West End',
      dateLabel: 'Tomorrow, Oct 25',
      timeLabel: '09:00 - 10:30',
    ),
    const Booking(
      id: 'BKG-8478',
      pestType: 'General Pest Inspection',
      area: '88 Industrial Blvd, Eastside',
      dateLabel: 'Tomorrow, Oct 25',
      timeLabel: '11:00 - 12:00',
    ),
  ];

  static final List<Booking> acceptedBookings = [
    Booking(
      id: 'BKG-4921',
      pestType: 'Termites',
      area: '124 Oakwood Drive, Maplewood District',
      dateLabel: 'Today',
      timeLabel: '2:00 PM',
      customerName: 'Sarah Jenkins',
      address: '124 Oakwood Drive, Maplewood District',
      phone: '+1 555 010 2345',
      bookingType: BookingType.amcVisit,
      priority: BookingPriority.high,
      acceptedState: AcceptedJobState.pending,
      timeRemaining: '1h 30m left',
      scheduleLabel: 'Today, 2:00 PM',
      scheduleSubLabel: 'In 1h 30m',
      propertyType: 'Residential (Villa)',
      bhk: '4 BHK',
      notes:
          'Customer mentioned sightings in the kitchen and backyard. Please check the attic as well.',
      treatment: 'Chemical Spray + Baiting',
      amount: '₹4,500',
      paymentStatus: PaymentStatus.unpaid,
    ),
    Booking(
      id: 'BKG-4918',
      pestType: 'Cockroach Control',
      area: '89B Tech Park Blvd, Suite 400',
      dateLabel: 'Today',
      timeLabel: '4:30 PM',
      customerName: 'Michael Chang',
      address: '89B Tech Park Blvd, Suite 400',
      phone: '+1 555 010 9876',
      bookingType: BookingType.serviceCall,
      acceptedState: AcceptedJobState.inService,
      scheduleLabel: 'Today, 4:30 PM',
      scheduleSubLabel: 'Ongoing',
    ),
  ];

  static final List<Booking> completedBookings = [
  const Booking(
      id: 'BKG-8892',
      pestType: 'Rodent Control',
      customerName: 'Sarah Jenkins',
      area: '',
      dateLabel: 'Oct 12, 14:30',
      timeLabel: '',
      completionDate: 'Oct 12, 14:30',
      paymentMode: PaymentMode.online,
      isPaid: true,
    ),
    const Booking(
      id: 'BKG-8889',
      pestType: 'Termite Inspection',
      customerName: 'Michael Chang',
      area: '',
      dateLabel: 'Oct 11, 09:15',
      timeLabel: '',
      completionDate: 'Oct 11, 09:15',
      paymentMode: PaymentMode.cash,
      isPaid: true,
    ),
    Booking(
      id: 'BKG-8875',
      pestType: 'General Spray',
      customerName: 'Riverfront Apartments',
      area: '',
      dateLabel: 'Oct 10, 16:00',
      timeLabel: '',
      completionDate: 'Oct 10, 16:00',
      paymentStatus: PaymentStatus.pending,
      isPaid: false,
    ),
  ];
}
