import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/models/booking_type.dart';
import '../models/booking.dart' as api;
import '../models/booking_action_result.dart';
import '../providers/bookings_provider.dart';
import 'widgets/processing_overlay.dart';
import 'widgets/service_modals.dart';

/// Centralized start / end / accept / reject flows for list and detail screens.
class BookingWorkflow {
  BookingWorkflow._();

  static Future<void> handleAcceptedPrimary(
    BuildContext context,
    api.PartnerBooking booking,
  ) async {
    if (booking.allowsComplete) {
      await completeFromCard(context, booking.id);
      return;
    }
    if (booking.allowsStart) {
      await startFromCard(context, booking.id);
    }
  }

  static Future<void> startFromCard(BuildContext context, int bookingId) async {
    final path = await showSelfieVerificationModal(context);
    if (path == null || !context.mounted) return;
    await _runStart(context, bookingId, path);
  }

  static Future<void> startFromDetail(
    BuildContext context,
    int bookingId,
  ) async {
    final path = await showSelfieVerificationModal(context);
    if (path == null || !context.mounted) return;
    await _runStart(context, bookingId, path);
  }

  static Future<void> completeFromCard(BuildContext context, int bookingId) async {
    final mode = await showEndServiceModal(context);
    if (mode == null || !context.mounted) return;
    await _runComplete(context, bookingId, mode);
  }

  static Future<void> completeFromDetail(
    BuildContext context,
    int bookingId,
  ) async {
    final mode = await showEndServiceModal(context);
    if (mode == null || !context.mounted) return;
    await _runComplete(context, bookingId, mode);
  }

  static Future<BookingActionResult?> accept(
    BuildContext context,
    int bookingId,
  ) async {
    final provider = context.read<BookingsProvider>();
    if (provider.isProcessing(bookingId)) return null;

    final result = await runWithProcessingOverlay(
      context,
      title: 'Accepting job…',
      subtitle: 'Please wait',
      task: () => provider.accept(bookingId),
    );
    if (!context.mounted) return result;
    _showResult(context, result);
    if (result.success && result.navigateToAccepted) {
      context.go('/accepted');
    }
    return result;
  }

  static Future<BookingActionResult?> reject(
    BuildContext context,
    int bookingId,
  ) async {
    final provider = context.read<BookingsProvider>();
    if (provider.isProcessing(bookingId)) return null;

    final result = await runWithProcessingOverlay(
      context,
      title: 'Rejecting booking…',
      subtitle: 'Please wait',
      task: () => provider.reject(bookingId),
    );
    if (context.mounted) _showResult(context, result);
    return result;
  }

  static Future<void> _runStart(
    BuildContext context,
    int bookingId,
    String selfiePath,
  ) async {
    final provider = context.read<BookingsProvider>();
    if (provider.isProcessing(bookingId)) return;

    final result = await runWithProcessingOverlay(
      context,
      title: 'Uploading selfie…',
      subtitle: 'Starting your visit',
      task: () async {
        return provider.startJob(bookingId, selfiePath);
      },
    );

    if (!context.mounted) return;
    _showResult(context, result, successIcon: Icons.check_circle);
  }

  static Future<void> _runComplete(
    BuildContext context,
    int bookingId,
    PaymentMode mode,
  ) async {
    final provider = context.read<BookingsProvider>();
    if (provider.isProcessing(bookingId)) return;

    final payment = mode == PaymentMode.online ? 'Online' : 'Cash';
    final result = await runWithProcessingOverlay(
      context,
      title: 'Ending service…',
      subtitle: 'Saving payment',
      task: () => provider.completeJob(bookingId, payment),
    );

    if (!context.mounted) return;
    _showResult(context, result, successIcon: Icons.check_circle);
    if (result.success && result.navigateToCompleted) {
      context.go('/completed');
    }
  }

  static void _showResult(
    BuildContext context,
    BookingActionResult result, {
    IconData? successIcon,
  }) {
    final msg = result.message;
    if (msg == null || msg.isEmpty) return;
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            if (result.success && successIcon != null) ...[
              Icon(successIcon, color: Colors.white, size: 20),
              const SizedBox(width: 8),
            ],
            Expanded(child: Text(msg)),
          ],
        ),
        backgroundColor: result.success ? null : Theme.of(context).colorScheme.error,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
