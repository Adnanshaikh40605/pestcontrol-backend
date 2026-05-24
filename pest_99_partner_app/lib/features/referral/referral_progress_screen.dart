import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../models/partner_referral.dart';
import '../../services/referral_service.dart';
import '../../core/api_client.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/primary_button.dart';

class ReferralProgressScreen extends StatefulWidget {
  const ReferralProgressScreen({super.key, this.highlightId});

  final int? highlightId;

  @override
  State<ReferralProgressScreen> createState() => _ReferralProgressScreenState();
}

class _ReferralProgressScreenState extends State<ReferralProgressScreen> {
  List<PartnerReferral> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await ReferralService(context.read<ApiClient>()).listReferrals();
      if (!mounted) return;
      setState(() {
        _items = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('dd MMM yyyy, hh:mm a');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Referral Progress'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: _loading && _items.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _items.isEmpty
              ? AsyncErrorView(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: _items.isEmpty
                      ? ListView(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.all(AppSpacing.screenEdge),
                          children: [
                            const SizedBox(height: 48),
                            Icon(Icons.card_giftcard_outlined, size: 56, color: AppColors.textSecondary),
                            const SizedBox(height: 16),
                            Text(
                              'No referrals yet',
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Refer a client from your profile to track progress here.',
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: AppColors.textSecondary,
                                  ),
                            ),
                            const SizedBox(height: 24),
                            PrimaryButton(
                              label: 'Refer a client',
                              onPressed: () => context.push('/refer-client'),
                            ),
                          ],
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(AppSpacing.screenEdge),
                          itemCount: _items.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (context, index) {
                            final r = _items[index];
                            final highlighted = widget.highlightId == r.id;
                            return _ReferralCard(
                              referral: r,
                              highlighted: highlighted,
                              dateLabel: r.referredAt != null ? dateFmt.format(r.referredAt!.toLocal()) : '',
                            );
                          },
                        ),
                ),
      floatingActionButton: _items.isNotEmpty
          ? FloatingActionButton.extended(
              onPressed: () => context.push('/refer-client'),
              icon: const Icon(Icons.add),
              label: const Text('New referral'),
            )
          : null,
    );
  }
}

class _ReferralCard extends StatelessWidget {
  const _ReferralCard({
    required this.referral,
    required this.highlighted,
    required this.dateLabel,
  });

  final PartnerReferral referral;
  final bool highlighted;
  final String dateLabel;

  @override
  Widget build(BuildContext context) {
    final statusStyle = _statusStyle(referral.status);

    return Material(
      color: highlighted ? AppColors.primaryContainer.withValues(alpha: 0.5) : AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: highlighted ? AppColors.primary : AppColors.border,
          width: highlighted ? 1.5 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    referral.clientName,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusStyle.bg,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    referral.statusLabel,
                    style: TextStyle(
                      color: statusStyle.fg,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(referral.mobile, style: Theme.of(context).textTheme.bodyMedium),
            if (referral.area.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                referral.area,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
            if (dateLabel.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                'Referred $dateLabel',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              _statusHint(referral.status),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }

  static ({Color bg, Color fg}) _statusStyle(String status) {
    switch (status) {
      case 'successful':
        return (bg: AppColors.successBg, fg: AppColors.successText);
      case 'in_progress':
        return (bg: const Color(0xFFFFF7ED), fg: AppColors.tagOrange);
      case 'closed':
        return (bg: const Color(0xFFF3F4F6), fg: AppColors.textSecondary);
      default:
        return (bg: const Color(0xFFEFF6FF), fg: AppColors.infoBlue);
    }
  }

  static String _statusHint(String status) {
    switch (status) {
      case 'successful':
        return 'This referral was converted — thank you!';
      case 'in_progress':
        return 'Our team is following up with your referral.';
      case 'closed':
        return 'This referral was closed without conversion.';
      default:
        return 'Pending review by our office team.';
    }
  }
}
