import 'package:flutter/material.dart';

import '../../core/theme/app_spacing.dart';
import '../../models/booking.dart' as api;

class CallKindSplit {
  const CallKindSplit({
    required this.serviceCalls,
    required this.complaintCalls,
    required this.other,
  });

  final List<api.PartnerBooking> serviceCalls;
  final List<api.PartnerBooking> complaintCalls;
  final List<api.PartnerBooking> other;

  factory CallKindSplit.from(List<api.PartnerBooking> rows) {
    final serviceCalls = <api.PartnerBooking>[];
    final complaintCalls = <api.PartnerBooking>[];
    final other = <api.PartnerBooking>[];
    for (final row in rows) {
      if (row.isComplaintCall) {
        complaintCalls.add(row);
      } else if (row.isServiceCall) {
        serviceCalls.add(row);
      } else {
        other.add(row);
      }
    }
    return CallKindSplit(
      serviceCalls: serviceCalls,
      complaintCalls: complaintCalls,
      other: other,
    );
  }

  bool get isEmpty =>
      serviceCalls.isEmpty && complaintCalls.isEmpty && other.isEmpty;
}

class CallSectionHeader extends StatelessWidget {
  const CallSectionHeader({
    super.key,
    required this.title,
    required this.count,
    required this.subtitle,
    required this.color,
  });

  final String title;
  final int count;
  final String subtitle;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.elementGap),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '$title ($count)',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: const Color(0xFF111827),
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: const Color(0xFF6B7280),
                ),
          ),
        ],
      ),
    );
  }
}
