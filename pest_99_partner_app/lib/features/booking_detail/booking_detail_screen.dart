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
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await context.read<BookingsProvider>().refreshAll();
      await _fetchLatest(silent: false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = userErrorMessage(e, fallback: 'Could not refresh booking.');
          _loading = false;
        });
      }
    }
  }

  Future<void> _afterWorkflowAction() async {
    await context.read<BookingsProvider>().refreshAll();
    if (!mounted) return;
    await _fetchLatest(silent: false);
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
                const SizedBox(height: 8),
                Text('Amount: ${b.priceDisplay ?? b.price ?? '—'}'),
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
                      await BookingWorkflow.reject(context, b.id);
                      if (!mounted) return;
                      if (!context.read<BookingsProvider>().available.any((x) => x.id == b.id)) {
                        context.pop();
                      } else {
                        await _afterWorkflowAction();
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
                    if (mounted) await _afterWorkflowAction();
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
              if (trailing != null) trailing!,
            ],
          ),
          const SizedBox(height: AppSpacing.elementGap),
          child,
        ],
      ),
    );
  }
}
