/// Route extra when opening booking detail (especially from push / in-app alerts).
class BookingOpenArgs {
  const BookingOpenArgs({
    this.fromNotification = false,
    this.refreshToken,
  });

  final bool fromNotification;
  final int? refreshToken;

  factory BookingOpenArgs.fromNotification() => BookingOpenArgs(
        fromNotification: true,
        refreshToken: DateTime.now().millisecondsSinceEpoch,
      );

  String pageKey(int bookingId) =>
      'booking-$bookingId-${refreshToken ?? 'default'}';
}
