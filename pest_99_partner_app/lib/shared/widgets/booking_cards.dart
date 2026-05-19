import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/booking.dart';
import '../../core/models/booking_type.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import 'booking_type_tag.dart';
import 'loading_action_button.dart';
import 'primary_button.dart';

class AvailableBookingCard extends StatelessWidget {
  const AvailableBookingCard({
    super.key,
    required this.booking,
    this.onAccept,
    this.onReject,
    this.isAcceptLoading = false,
    this.isRejectLoading = false,
  });

  final Booking booking;
  final VoidCallback? onAccept;
  final VoidCallback? onReject;
  final bool isAcceptLoading;
  final bool isRejectLoading;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(color: Color(0x0A000000), blurRadius: 12, offset: Offset(0, 4)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '#${booking.id}',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            letterSpacing: 1.2,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(booking.pestType, style: Theme.of(context).textTheme.headlineSmall),
                  ],
                ),
              ),
              PriorityBadge(priority: booking.priority),
            ],
          ),
          const SizedBox(height: 12),
          _InfoRow(icon: Icons.location_on_outlined, text: booking.area),
          const SizedBox(height: 8),
          Row(
            children: [
              const Icon(Icons.event_outlined, size: 20, color: AppColors.textSecondary),
              const SizedBox(width: 8),
              Text(booking.dateLabel, style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.onSurfaceVariant,
                  )),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text('|', style: TextStyle(color: AppColors.border.withValues(alpha: 0.8))),
              ),
              const Icon(Icons.schedule, size: 20, color: AppColors.textSecondary),
              const SizedBox(width: 8),
              Text(
                booking.timeLabel,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const Padding(
            padding: EdgeInsets.only(top: 16),
            child: Divider(height: 1, color: AppColors.border),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedActionButton(
                  label: isRejectLoading ? 'Rejecting…' : 'Reject',
                  icon: Icons.close,
                  onPressed: isRejectLoading || isAcceptLoading ? null : onReject,
                ),
              ),
              const SizedBox(width: AppSpacing.elementGap),
              Expanded(
                flex: 2,
                child: LoadingActionButton(
                  label: 'Accept Job',
                  loadingLabel: 'Accepting…',
                  icon: Icons.check,
                  isLoading: isAcceptLoading,
                  onPressed: isRejectLoading ? null : onAccept,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class AcceptedBookingCard extends StatelessWidget {
  const AcceptedBookingCard({
    super.key,
    required this.booking,
    this.onViewDetails,
    this.onPrimaryAction,
    this.isPrimaryLoading = false,
    this.primaryLoadingLabel,
  });

  final Booking booking;
  final VoidCallback? onViewDetails;
  final VoidCallback? onPrimaryAction;
  final bool isPrimaryLoading;
  final String? primaryLoadingLabel;

  @override
  Widget build(BuildContext context) {
    final inService = booking.acceptedState == AcceptedJobState.inService;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpacing.baseRadius),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(color: Color(0x0A000000), blurRadius: 30, offset: Offset(0, 8)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        if (booking.priority == BookingPriority.high)
                          StatusChip(
                            label: 'High Priority',
                            backgroundColor: AppColors.errorContainer,
                            foregroundColor: AppColors.onErrorContainer,
                          ),
                        BookingTypeTag(type: booking.bookingType),
                        Text(
                          '#${booking.id}',
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      booking.customerName ?? '',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    if (inService) ...[
                      Row(
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: AppColors.successText,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Started at 2:15 PM',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: AppColors.successText,
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                        ],
                      ),
                      Text(
                        'Running for 25 mins',
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: AppColors.textSecondary,
                            ),
                      ),
                    ] else if (booking.timeRemaining != null)
                      StatusChip(
                        label: booking.timeRemaining!,
                        backgroundColor: AppColors.successBg,
                        foregroundColor: AppColors.successText,
                        icon: Icons.schedule,
                      ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    booking.scheduleLabel ?? '',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppColors.primary),
                  ),
                  Text(
                    booking.scheduleSubLabel ?? '',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: inService ? AppColors.infoBlue : AppColors.textSecondary,
                          fontWeight: inService ? FontWeight.w500 : FontWeight.w400,
                        ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          _InfoRow(icon: Icons.location_on_outlined, text: booking.address ?? booking.area),
          if (!inService) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _SecondaryActionButton(
                    icon: Icons.call,
                    label: 'Call',
                    onTap: () {},
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _SecondaryActionButton(
                    icon: Icons.directions,
                    label: 'Maps',
                    onTap: () {},
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: GreenOutlineButton(
                  label: 'View Details',
                  onPressed: onViewDetails ?? () => context.push('/booking/${Uri.encodeComponent(booking.id)}'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: LoadingActionButton(
                  label: inService ? 'End Service' : 'Start Job',
                  loadingLabel: primaryLoadingLabel ??
                      (inService ? 'Ending service…' : 'Starting job…'),
                  icon: inService ? Icons.check_circle_outline : Icons.play_arrow,
                  isLoading: isPrimaryLoading,
                  onPressed: onPrimaryAction,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class CompletedBookingCard extends StatelessWidget {
  const CompletedBookingCard({super.key, required this.booking});

  final Booking booking;

  @override
  Widget build(BuildContext context) {
    final paid = booking.isPaid;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(color: Color(0x0A000000), blurRadius: 12, offset: Offset(0, 4)),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: IntrinsicHeight(
          child: Row(
            children: [
              Container(width: 4, color: paid ? AppColors.primary : AppColors.outlineVariant),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.cardPadding),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Wrap(
                                  spacing: 8,
                                  children: [
                                    Text('#${booking.id}', style: Theme.of(context).textTheme.labelSmall),
                                    StatusChip(
                                      label: booking.pestType,
                                      backgroundColor: AppColors.primary.withValues(alpha: 0.1),
                                      foregroundColor: AppColors.primary,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  booking.customerName ?? '',
                                  style: Theme.of(context).textTheme.bodyLarge,
                                ),
                              ],
                            ),
                          ),
                          StatusChip(
                            label: paid ? 'Paid' : 'Pending',
                            backgroundColor: paid ? AppColors.successBg : AppColors.surfaceContainerHigh,
                            foregroundColor: paid ? AppColors.successText : AppColors.onSurfaceVariant,
                            icon: paid ? Icons.check_circle : Icons.pending,
                            borderColor: paid ? AppColors.successText.withValues(alpha: 0.2) : AppColors.outlineVariant.withValues(alpha: 0.5),
                          ),
                        ],
                      ),
                      const Padding(
                        padding: EdgeInsets.only(top: 16),
                        child: Divider(height: 1, color: AppColors.border),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: _MetaBlock(
                              icon: Icons.calendar_month_outlined,
                              label: 'COMPLETION',
                              value: booking.completionDate ?? booking.dateLabel,
                            ),
                          ),
                          Expanded(
                            child: _MetaBlock(
                              icon: Icons.payments_outlined,
                              label: 'PAYMENT MODE',
                              value: booking.paymentMode == PaymentMode.cash
                                  ? 'Cash'
                                  : booking.paymentMode == PaymentMode.online
                                      ? 'Online (Card)'
                                      : '—',
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: AppColors.textSecondary),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.onSurfaceVariant),
          ),
        ),
      ],
    );
  }
}

class _SecondaryActionButton extends StatelessWidget {
  const _SecondaryActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surfaceContainerLow,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 18, color: AppColors.primary),
              const SizedBox(width: 8),
              Text(label, style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppColors.primary)),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetaBlock extends StatelessWidget {
  const _MetaBlock({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: AppColors.textSecondary),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(context).textTheme.labelSmall),
              Text(value, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
      ],
    );
  }
}
