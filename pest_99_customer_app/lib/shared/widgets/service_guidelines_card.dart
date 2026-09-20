import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/booking_flow_provider.dart';

/// Website-aligned Do's & Don'ts shown before and after booking.
///
/// Sources: HomeQuoteForm TREATMENT_DETAILS (Standard/Premium) plus
/// general prep guidance used across pest service pages.
class ServiceGuidelines {
  static const generalDos = <String>[
    'Cover or remove open food items and drinking water before the visit.',
    'Keep children and pets away from treated areas during and after service.',
    'Provide clear access to kitchens, bathrooms, and pest-prone corners.',
    'Share any previous treatments or allergies with the technician.',
  ];

  static const generalDonts = <String>[
    'Do not wash or mop treated surfaces for at least 3 hours after spray treatment.',
    'Do not move bait stations / gel spots unless the technician asks you to.',
    'Do not use strong cleaning chemicals on treated areas the same day.',
    'Do not leave windows/doors wide open during outdoor-sensitive treatments unless advised.',
  ];

  /// Extra bullets from Standard / Premium treatment copy when applicable.
  static List<String> treatmentDos(String? quality) {
    final key = (quality ?? '').toLowerCase();
    final detail = BookingFlowProvider.treatmentDetails[key];
    if (detail == null) return const [];
    return detail.bullets;
  }

  static ({List<String> dos, List<String> donts}) forQuality(String? quality) {
    final treatment = treatmentDos(quality);
    final dos = <String>[...generalDos];
    final donts = <String>[...generalDonts];
    // Promote treatment-specific prep into Do's when present.
    for (final b in treatment) {
      final lower = b.toLowerCase();
      if (lower.contains('do not') || lower.contains("don't") || lower.contains('must not')) {
        donts.add(b);
      } else {
        dos.add(b);
      }
    }
    return (dos: dos, donts: donts);
  }
}

class ServiceGuidelinesCard extends StatelessWidget {
  const ServiceGuidelinesCard({
    super.key,
    this.treatmentQuality,
    this.title = "Service Do's & Don'ts",
    this.compact = false,
  });

  final String? treatmentQuality;
  final String title;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final g = ServiceGuidelines.forQuality(treatmentQuality);
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(compact ? 12 : 14),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDF4),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFBBF7D0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: AppColors.primary,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            'Please read before the technician arrives — and keep these tips handy after service.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
          const SizedBox(height: 12),
          Text(
            "Do's",
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: const Color(0xFF166534),
                ),
          ),
          const SizedBox(height: 6),
          ...g.dos.take(compact ? 4 : g.dos.length).map(
                (d) => _Bullet(text: d, positive: true),
              ),
          const SizedBox(height: 12),
          Text(
            "Don'ts",
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: const Color(0xFF9A3412),
                ),
          ),
          const SizedBox(height: 6),
          ...g.donts.take(compact ? 4 : g.donts.length).map(
                (d) => _Bullet(text: d, positive: false),
              ),
        ],
      ),
    );
  }
}

class _Bullet extends StatelessWidget {
  const _Bullet({required this.text, required this.positive});

  final String text;
  final bool positive;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            positive ? Icons.check_circle_outline : Icons.highlight_off_outlined,
            size: 16,
            color: positive ? const Color(0xFF166534) : const Color(0xFF9A3412),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 12.5, height: 1.35, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
