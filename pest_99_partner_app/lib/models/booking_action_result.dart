enum BookingActionKind { accept, reject, start, complete }

class BookingActionResult {
  const BookingActionResult({
    required this.success,
    this.message,
    this.navigateToCompleted = false,
    this.navigateToAccepted = false,
  });

  final bool success;
  final String? message;
  final bool navigateToCompleted;
  final bool navigateToAccepted;

  factory BookingActionResult.ok({
    String? message,
    bool navigateToCompleted = false,
    bool navigateToAccepted = false,
  }) =>
      BookingActionResult(
        success: true,
        message: message,
        navigateToCompleted: navigateToCompleted,
        navigateToAccepted: navigateToAccepted,
      );

  factory BookingActionResult.fail(String message) =>
      BookingActionResult(success: false, message: message);
}
