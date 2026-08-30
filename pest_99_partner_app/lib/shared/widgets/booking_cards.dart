import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/booking.dart';
import '../../core/models/booking_type.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/utils/money_format.dart';
import 'booking_type_tag.dart';
import 'loading_action_button.dart';
import 'primary_button.dart';

String formatMoneyLabel(String? raw) => MoneyFormat.rupees(raw);

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
    final busy = isAcceptLoading || isRejectLoading;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0D000000),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '#${booking.id}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
              const SizedBox(width: 8),
              PriorityBadge(priority: booking.priority),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            booking.pestType.isEmpty ? 'Service' : booking.pestType,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w800,
                  height: 1.2,
                  fontSize: 20,
                ),
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.only(top: 1),
                child: Icon(Icons.location_on, size: 18, color: AppColors.primary),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  booking.area,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.onSurfaceVariant,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
            ],
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 14),
            child: Divider(height: 1, thickness: 1, color: AppColors.border),
          ),
          Row(
            children: [
              const Icon(Icons.calendar_today_outlined, size: 16, color: AppColors.textSecondary),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  booking.dateLabel,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.onSurfaceVariant,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  '|',
                  style: TextStyle(
                    color: AppColors.border.withValues(alpha: 0.95),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const Icon(Icons.access_time, size: 16, color: AppColors.textSecondary),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  booking.timeLabel,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.onSurfaceVariant,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 48,
                  child: OutlinedButton(
                    onPressed: busy ? null : onReject,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.textPrimary,
                      side: const BorderSide(color: AppColors.border, width: 1.2),
                      backgroundColor: AppColors.surface,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (isRejectLoading)
                          const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        else
                          const Icon(Icons.close, size: 18),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            isRejectLoading ? 'Rejecting…' : 'Reject',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: SizedBox(
                  height: 48,
                  child: ElevatedButton(
                    onPressed: busy ? null : onAccept,                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: AppColors.onPrimary,
                      disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.45),
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (isAcceptLoading)
                          const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        else
                          const Icon(Icons.check, size: 18, color: Colors.white),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            isAcceptLoading ? 'Accepting…' : 'Accept Job',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
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
    this.onCall,
    this.onMaps,
    this.onPrimaryAction,
    this.isPrimaryLoading = false,
    this.primaryLoadingLabel,
  });

  final Booking booking;
  final VoidCallback? onViewDetails;
  final VoidCallback? onCall;
  final VoidCallback? onMaps;
  final VoidCallback? onPrimaryAction;
  final bool isPrimaryLoading;
  final String? primaryLoadingLabel;

  @override
  Widget build(BuildContext context) {
    final inService = booking.acceptedState == AcceptedJobState.inService;
    final borderColor = booking.isToday
        ? const Color(0xFF16A34A)
        : booking.isTomorrow
            ? const Color(0xFF2563EB)
            : AppColors.border;
    final tint = booking.isToday
        ? const Color(0xFFF0FDF4)
        : booking.isTomorrow
            ? const Color(0xFFEFF6FF)
            : AppColors.surface;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: tint,
        borderRadius: BorderRadius.circular(AppSpacing.baseRadius),
        border: Border.all(color: borderColor, width: booking.isToday || booking.isTomorrow ? 1.5 : 1),
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
                        BookingTypeTag(type: booking.bookingType, labelOverride: booking.displayPlanLabel),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            formatMoneyLabel(booking.displayAmount),
                            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.w800,
                                ),
                          ),
                        ),
                        if (booking.isToday || booking.isTomorrow)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: borderColor.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              booking.isToday ? 'TODAY' : 'TOMORROW',
                              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: borderColor,
                                    fontWeight: FontWeight.w800,
                                    fontSize: 10,
                                  ),
                            ),
                          ),
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
                          Expanded(
                            child: Text(
                              booking.startedAtLabel ?? 'Service in progress',
                              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: AppColors.successText,
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                          ),
                        ],
                      ),
                      if (booking.runningForLabel != null)
                        Text(
                          booking.runningForLabel!,
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
                    onTap: onCall,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _SecondaryActionButton(
                    icon: Icons.directions,
                    label: 'Maps',
                    onTap: onMaps,
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
    final yourShare = booking.hasRevenuePayout ? booking.yourShareAmount : null;
    final jobAmount = booking.jobAmount ?? booking.amount;

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
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              if (yourShare != null) ...[
                                Text(
                                  MoneyFormat.rupees(yourShare),
                                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                        fontWeight: FontWeight.w800,
                                        color: AppColors.primary,
                                      ),
                                ),
                                Text(
                                  booking.yourShareLabel,
                                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                        color: AppColors.textSecondary,
                                      ),
                                ),
                              ] else
                                StatusChip(
                                  label: paid ? 'Paid' : 'Pending',
                                  backgroundColor: paid ? AppColors.successBg : AppColors.surfaceContainerHigh,
                                  foregroundColor: paid ? AppColors.successText : AppColors.onSurfaceVariant,
                                  icon: paid ? Icons.check_circle : Icons.pending,
                                  borderColor: paid
                                      ? AppColors.successText.withValues(alpha: 0.2)
                                      : AppColors.outlineVariant.withValues(alpha: 0.5),
                                ),
                            ],
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
                              label: 'CUSTOMER PAID',
                              value: paid ? 'Yes' : 'Pending',
                            ),
                          ),
                        ],
                      ),
                      if (yourShare != null || jobAmount != null) ...[
                        const SizedBox(height: 12),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceContainerLow,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Column(
                            children: [
                              if (jobAmount != null)
                                _MoneyLine(
                                  label: 'Job / service amount',
                                  value: MoneyFormat.rupees(jobAmount),
                                  muted: true,
                                ),
                              if (yourShare != null) ...[
                                if (jobAmount != null) const SizedBox(height: 6),
                                _MoneyLine(
                                  label: booking.yourShareLabel,
                                  value: MoneyFormat.rupees(yourShare),
                                  emphasize: true,
                                ),
                              ],
                              if (booking.companyShareAmount != null &&
                                  booking.companyShareAmount!.isNotEmpty &&
                                  booking.companyShareAmount != '0' &&
                                  booking.companyShareAmount != '0.00') ...[
                                const SizedBox(height: 6),
                                _MoneyLine(
                                  label: booking.companyShareLabel,
                                  value: MoneyFormat.rupees(booking.companyShareAmount),
                                  muted: true,
                                ),
                              ],
                              if (booking.payoutStatus != null && booking.payoutStatus!.isNotEmpty) ...[
                                const SizedBox(height: 6),
                                _MoneyLine(
                                  label: 'Payout status',
                                  value: booking.payoutStatus!,
                                  muted: true,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
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

class _MoneyLine extends StatelessWidget {
  const _MoneyLine({
    required this.label,
    required this.value,
    this.emphasize = false,
    this.muted = false,
  });

  final String label;
  final String value;
  final bool emphasize;
  final bool muted;

  @override
  Widget build(BuildContext context) {
    final labelStyle = Theme.of(context).textTheme.labelMedium?.copyWith(
          color: muted ? AppColors.textSecondary : AppColors.onSurface,
        );
    final valueStyle = Theme.of(context).textTheme.bodyMedium?.copyWith(
          fontWeight: emphasize ? FontWeight.w800 : FontWeight.w600,
          color: emphasize ? AppColors.primary : (muted ? AppColors.textSecondary : AppColors.onSurface),
        );
    return Row(
      children: [
        Expanded(child: Text(label, style: labelStyle)),
        Text(value, style: valueStyle),
      ],
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
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return Material(
      color: AppColors.surfaceContainerLow,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: enabled ? onTap : null,
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
