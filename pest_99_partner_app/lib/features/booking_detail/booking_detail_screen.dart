import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api_client.dart';
import '../../core/models/booking_type.dart';
import '../../core/routing/booking_open_args.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/user_error.dart';
import '../../core/utils/money_format.dart';
import '../../models/booking.dart' as api;
import '../../providers/bookings_provider.dart';
import '../../services/booking_service.dart';
import '../../shared/booking_workflow.dart';
import '../../shared/widgets/app_top_bar.dart';
import '../../shared/widgets/async_error_view.dart';
import '../../shared/widgets/booking_type_tag.dart';
import '../../shared/widgets/loading_action_button.dart';

class BookingDetailScreen extends StatefulWidget {
  const BookingDetailScreen({
    super.key,
    required this.bookingId,
    this.openArgs,
  });

  final int bookingId;
  final BookingOpenArgs? openArgs;

  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen> {
  api.PartnerBooking? _booking;
  bool _loading = true;
  String? _error;

  bool get _forceFreshLoad => widget.openArgs?.fromNotification == true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant BookingDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.bookingId != widget.bookingId ||
        oldWidget.openArgs?.refreshToken != widget.openArgs?.refreshToken) {
      _load();
    }
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      if (!_forceFreshLoad) {
        final cached = _bookingFromProvider();
        if (cached != null) {
          if (mounted) {
            setState(() {
              _booking = cached;
              _loading = false;
            });
          }
          _fetchLatest(silent: true);
          return;
        }
      }

      await _fetchLatest(silent: false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = userErrorMessage(e, fallback: 'Could not load booking.');
          _loading = false;
        });
      }
    }
  }

  api.PartnerBooking? _bookingFromProvider() {
    final provider = context.read<BookingsProvider>();
    for (final list in [provider.available, provider.accepted, provider.completed]) {
      for (final b in list) {
        if (b.id == widget.bookingId) return b;
      }
    }
    return null;
  }

  Future<void> _fetchLatest({required bool silent}) async {
    try {
      final apiClient = context.read<ApiClient>();
      final detail = await BookingService(apiClient).getDetail(widget.bookingId);
      if (!mounted) return;
      setState(() {
        _booking = detail;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      if (!silent) {
        setState(() {
          _error = userErrorMessage(e, fallback: 'Could not load booking.');
          _loading = false;
        });
      }
    }
  }

  Future<void> _onRefresh() async {
    await _fetchLatest(silent: false);
  }

  Future<void> _afterWorkflowAction() async {
    if (!mounted) return;
    await _fetchLatest(silent: false);
    final provider = context.read<BookingsProvider>();
    final detail = _booking;
    if (detail != null) {
      if (provider.available.any((x) => x.id == detail.id)) {
        provider.removeFromAvailable(detail.id);
      }
      if (detail.partnerStatus == 'accepted' ||
          detail.partnerStatus == 'in_service' ||
          detail.allowsStart ||
          detail.allowsComplete) {
        provider.applyAcceptedBooking(detail);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<BookingsProvider>();
    final processing = provider.isProcessing(widget.bookingId);
    final processingLabel = provider.processingLabel(widget.bookingId);
    final b = _booking;

    return PopScope(
      canPop: !processing,
      child: Scaffold(
        appBar: AppTopBar(
          showAvatar: false,
          showBack: true,
          centerLogo: true,
          onBack: processing ? null : () => context.pop(),
        ),
        body: _buildBody(context, b, processing, processingLabel),
        bottomNavigationBar: _buildBottomBar(context, b, processing, processingLabel),
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    api.PartnerBooking? b,
    bool processing,
    String? processingLabel,
  ) {
    if (_loading && b == null && _error == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null && b == null) {
      return RefreshIndicator(
        onRefresh: _onRefresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: MediaQuery.sizeOf(context).height * 0.5,
              child: AsyncErrorView(
                message: _error!,
                onRetry: _load,
              ),
            ),
          ],
        ),
      );
    }

    if (b == null) {
      return RefreshIndicator(
        onRefresh: _onRefresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: MediaQuery.sizeOf(context).height * 0.4,
              child: const AsyncErrorView(
                message: 'Booking not found or no longer available.',
                icon: Icons.search_off,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.screenEdge,
          AppSpacing.sectionGap,
          AppSpacing.screenEdge,
          120,
        ),
        children: [
          if (_forceFreshLoad && !_loading)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Material(
                color: AppColors.primaryContainer.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: Row(
                    children: [
                      Icon(Icons.notifications_active, size: 18, color: Theme.of(context).colorScheme.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Latest booking details',
                          style: Theme.of(context).textTheme.labelLarge,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          _SectionCard(
            title: 'Customer',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(b.clientName ?? '—', style: Theme.of(context).textTheme.bodyLarge),
                if (b.canViewClientPhone && b.clientMobile != null) ...[
                  const SizedBox(height: 8),
                  Text(b.clientMobile!),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: processing
                        ? null
                        : () => launchUrl(Uri.parse('tel:${b.clientMobile}')),
                    icon: const Icon(Icons.call),
                    label: const Text('Call customer'),
                  ),
                ],
                const SizedBox(height: 12),
                Text(b.locationDisplay ?? b.clientAddress ?? '—'),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          _SectionCard(
            title: 'Service',
            trailing: BookingTypeTag(type: BookingType.booking),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(b.serviceType, style: Theme.of(context).textTheme.titleMedium),
                if (b.serviceCategory != null) Text(b.serviceCategory!),
                const SizedBox(height: 12),
                _MoneyBreakdownCard(booking: b),
                if (b.code != null && b.code!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text('Booking #${b.code}', style: Theme.of(context).textTheme.labelMedium),
                ],
                if (b.notes != null && b.notes!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(b.notes!, style: const TextStyle(fontStyle: FontStyle.italic)),
                ],
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          _SectionCard(
            title: 'Schedule',
            child: Text('${b.scheduleDatetime ?? '—'} · ${b.timeSlot ?? ''}'),
          ),
        ],
      ),
    );
  }

  Widget? _buildBottomBar(
    BuildContext context,
    api.PartnerBooking? b,
    bool processing,
    String? processingLabel,
  ) {
    if (b == null) return null;

    if (b.allowsAccept) {
      return _bottomActions(
        context,
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: processing
                  ? null
                  : () async {
                      final result = await BookingWorkflow.reject(context, b.id);
                      if (!mounted) return;
                      if (result?.success == true ||
                          !context.read<BookingsProvider>().available.any((x) => x.id == b.id)) {
                        context.pop();
                      } else {
                        await _fetchLatest(silent: true);
                      }
                    },
              child: const Text('Reject'),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: LoadingActionButton(
              label: 'Accept job',
              loadingLabel: processingLabel ?? 'Accepting…',
              icon: Icons.check,
              isLoading: processing,
              onPressed: processing
                  ? null
                  : () async {
                      final result = await BookingWorkflow.accept(context, b.id);
                      if (!mounted) return;
                      if (result?.success == true) {
                        await _afterWorkflowAction();
                        if (mounted) context.pop();
                      }
                    },
            ),
          ),
        ],
      );
    }

    if (!b.allowsStart && !b.allowsComplete) return null;

    return _bottomActions(
      context,
      children: [
        if (b.allowsStart)
          LoadingActionButton(
            label: 'Start job (selfie)',
            loadingLabel: processingLabel ?? 'Starting job…',
            icon: Icons.camera_alt,
            isLoading: processing,
            onPressed: processing
                ? null
                : () async {
                    await BookingWorkflow.startFromDetail(context, widget.bookingId);
                    if (mounted) await _fetchLatest(silent: true);
                  },
          )
        else
          LoadingActionButton(
            label: 'End Service',
            loadingLabel: processingLabel ?? 'Ending service…',
            icon: Icons.check_circle,
            isLoading: processing,
            onPressed: processing
                ? null
                : () async {
                    await BookingWorkflow.completeFromDetail(context, widget.bookingId);
                    if (!mounted) return;
                    if (!context.read<BookingsProvider>().accepted.any((x) => x.id == widget.bookingId)) {
                      context.pop();
                    } else {
                      await _afterWorkflowAction();
                    }
                  },
          ),
      ],
    );
  }

  Widget _bottomActions(BuildContext context, {required List<Widget> children}) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        AppSpacing.screenEdge,
        16,
        AppSpacing.screenEdge,
        MediaQuery.paddingOf(context).bottom + 16,
      ),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: Row(children: children),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child, this.trailing});

  final String title;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(title, style: Theme.of(context).textTheme.headlineSmall)),
              ?trailing,
            ],
          ),
          const SizedBox(height: AppSpacing.elementGap),
          child,
        ],
      ),
    );
  }
}

class _MoneyBreakdownCard extends StatelessWidget {
  const _MoneyBreakdownCard({required this.booking});

  final api.PartnerBooking booking;

  @override
  Widget build(BuildContext context) {
    final jobAmount = booking.priceDisplay ?? booking.price;
    final yourShare = booking.visitPayoutAmount;
    final companyShare = booking.companyShareAmount;
    final visitRev = booking.visitRevenueAmount;
    final showSplit = booking.hasRevenuePayout;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerLow,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Money for this service',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            showSplit
                ? 'Your money is only the technician share. Job amount is what the customer pays.'
                : 'No revenue-share payout on this visit (included / complaint / salaried).',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
          const SizedBox(height: 12),
          _DetailMoneyRow(
            label: 'Job / service amount',
            value: MoneyFormat.rupees(jobAmount),
            muted: true,
          ),
          if (visitRev != null &&
              visitRev.isNotEmpty &&
              visitRev != '0' &&
              visitRev != '0.00' &&
              visitRev != jobAmount?.replaceAll('₹', '')) ...[
            const SizedBox(height: 8),
            _DetailMoneyRow(
              label: 'This visit value',
              value: MoneyFormat.rupees(visitRev),
              muted: true,
            ),
          ],
          if (showSplit) ...[
            const SizedBox(height: 10),
            const Divider(height: 1),
            const SizedBox(height: 10),
            _DetailMoneyRow(
              label: booking.yourShareLabel,
              value: MoneyFormat.rupees(yourShare),
              emphasize: true,
            ),
            if (companyShare != null &&
                companyShare.isNotEmpty &&
                companyShare != '0' &&
                companyShare != '0.00') ...[
              const SizedBox(height: 8),
              _DetailMoneyRow(
                label: booking.companyShareLabel,
                value: MoneyFormat.rupees(companyShare),
                muted: true,
              ),
            ],
            if (booking.payoutStatus != null && booking.payoutStatus!.isNotEmpty) ...[
              const SizedBox(height: 8),
              _DetailMoneyRow(
                label: 'Payout status',
                value: booking.payoutStatus!,
                muted: true,
              ),
            ],
          ],
        ],
      ),
    );
  }
}

class _DetailMoneyRow extends StatelessWidget {
  const _DetailMoneyRow({
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
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: muted ? AppColors.textSecondary : AppColors.onSurface,
                ),
          ),
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: emphasize ? FontWeight.w800 : FontWeight.w600,
                color: emphasize
                    ? AppColors.primary
                    : (muted ? AppColors.textSecondary : AppColors.onSurface),
              ),
        ),
      ],
    );
  }
}
