import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/auth_gate.dart';
import '../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';
import '../providers/booking_flow_provider.dart';
import '../shared/widgets/pc99_widgets.dart';

/// Home dashboard — matches customer app design reference.
class HomeDashboardScreen extends StatelessWidget {
  const HomeDashboardScreen({super.key});

  static const _popular = <_PopularService>[
    _PopularService(
      id: 'cockroach',
      label: 'Cockroach Control',
      asset: 'assets/images/service_cockroach.png',
    ),
    _PopularService(
      id: 'termite',
      label: 'Termite Control',
      asset: 'assets/images/service_termite.png',
    ),
    _PopularService(
      id: 'bedbug',
      label: 'Bed Bug Treatment',
      asset: 'assets/images/service_bedbug.png',
    ),
    _PopularService(
      id: 'mosquito',
      label: 'Mosquito Control',
      asset: 'assets/images/service_mosquito.png',
    ),
    _PopularService(
      id: 'rodent',
      label: 'Rodent Control',
      asset: 'assets/images/service_rodent.png',
    ),
  ];

  void _bookService(BuildContext context, String? serviceId) {
    final flow = context.read<BookingFlowProvider>();
    flow.resetFlow();
    if (serviceId != null) {
      flow.selectOnlyService(serviceId);
    }
    pushAuthed(context, '/book/property');
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final profile = auth.profile;
    final name = (profile?.fullName.trim().isNotEmpty == true)
        ? profile!.fullName.split(' ').first
        : 'Guest';
    final width = MediaQuery.sizeOf(context).width;
    final horizontal = width < 360 ? 14.0 : 16.0;

    return Scaffold(
      backgroundColor: const Color(0xFFF7F8F6),
      body: SafeArea(
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.fromLTRB(horizontal, 8, horizontal, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const _HomeHeader(),
                    const SizedBox(height: 12),
                    Text(
                      'Hello, $name 👋',
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 12),
                    _HeroBanner(onBook: () => _bookService(context, null)),
                    const SizedBox(height: 22),
                    const Text(
                      'Popular Services',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    _PopularServicesGrid(
                      services: _popular,
                      onService: (id) => _bookService(context, id),
                      onViewAll: () => _bookService(context, null),
                    ),
                    const SizedBox(height: 22),
                    const _TrustBenefitsRow(),
                    const SizedBox(height: 28),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HomeHeader extends StatelessWidget {
  const _HomeHeader();

  @override
  Widget build(BuildContext context) {
    return const Align(
      alignment: Alignment.centerLeft,
      child: Pc99Logo(height: 36),
    );
  }
}

class _HeroBanner extends StatelessWidget {
  const _HeroBanner({required this.onBook});

  final VoidCallback onBook;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final height = (width * 0.38).clamp(132.0, 158.0);

    return Container(
      height: height,
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          colors: [Color(0xFF0A5A16), Color(0xFF0D631B), Color(0xFF178028)],
        ),
        boxShadow: const [
          BoxShadow(color: Color(0x260D631B), blurRadius: 14, offset: Offset(0, 6)),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // Technician cutout on the right — transparent PNG, no black box.
          Positioned(
            right: -6,
            bottom: -2,
            top: 4,
            width: width * 0.46,
            child: Image.asset(
              'assets/images/hero_technician.png',
              fit: BoxFit.contain,
              alignment: Alignment.bottomCenter,
              filterQuality: FilterQuality.high,
            ),
          ),
          // Soft fade so text stays readable over the figure.
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            width: width * 0.58,
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [
                    const Color(0xFF0A5A16),
                    const Color(0xFF0A5A16).withValues(alpha: 0.88),
                    const Color(0xFF0A5A16).withValues(alpha: 0.35),
                    const Color(0xFF0A5A16).withValues(alpha: 0.0),
                  ],
                  stops: const [0.0, 0.48, 0.78, 1.0],
                ),
              ),
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(width < 360 ? 14 : 16, 12, width * 0.40, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Expanded(
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'Professional pest control services',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 14.5,
                        fontWeight: FontWeight.w800,
                        height: 1.25,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  height: 34,
                  child: ElevatedButton(
                    onPressed: onBook,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppColors.primary,
                      elevation: 0,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
                    ),
                    child: const Text(
                      'Book Now',
                      style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PopularServicesGrid extends StatelessWidget {
  const _PopularServicesGrid({
    required this.services,
    required this.onService,
    required this.onViewAll,
  });

  final List<_PopularService> services;
  final void Function(String id) onService;
  final VoidCallback onViewAll;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final gap = width < 360 ? 8.0 : 10.0;
    final items = <Widget>[
      for (final s in services)
        _ServiceCard(
          label: s.label,
          asset: s.asset,
          onTap: () => onService(s.id),
        ),
      _ViewAllCard(onTap: onViewAll),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final tileW = (constraints.maxWidth - gap * 2) / 3;
        final tileH = tileW * 1.18;
        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: [
            for (final child in items)
              SizedBox(width: tileW, height: tileH, child: child),
          ],
        );
      },
    );
  }
}

class _ServiceCard extends StatelessWidget {
  const _ServiceCard({
    required this.label,
    required this.asset,
    required this.onTap,
  });

  final String label;
  final String asset;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      elevation: 0,
      shadowColor: Colors.black12,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Ink(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            boxShadow: const [
              BoxShadow(color: Color(0x14000000), blurRadius: 12, offset: Offset(0, 4)),
            ],
            border: Border.all(color: const Color(0xFFE8EBE6)),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 10, 8, 8),
            child: Column(
              children: [
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: Image.asset(
                      asset,
                      fit: BoxFit.contain,
                      filterQuality: FilterQuality.high,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  label,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    height: 1.2,
                    color: AppColors.textPrimary,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ViewAllCard extends StatelessWidget {
  const _ViewAllCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Ink(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            boxShadow: const [
              BoxShadow(color: Color(0x14000000), blurRadius: 12, offset: Offset(0, 4)),
            ],
            border: Border.all(color: const Color(0xFFE8EBE6)),
          ),
          child: const Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.more_horiz_rounded, size: 36, color: AppColors.primary),
              SizedBox(height: 6),
              Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  'View All Services',
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    height: 1.2,
                    color: AppColors.textPrimary,
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

class _TrustBenefitsRow extends StatelessWidget {
  const _TrustBenefitsRow();

  static const _items = <(IconData, String)>[
    (Icons.verified_user_outlined, 'Trusted Professionals'),
    (Icons.eco_outlined, 'Safe & Eco-Friendly'),
    (Icons.schedule_outlined, 'On-Time Service'),
    (Icons.thumb_up_alt_outlined, '100% Satisfaction'),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF6F0),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          for (final item in _items)
            Expanded(
              child: Column(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(item.$1, color: AppColors.primary, size: 20),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    item.$2,
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      height: 1.2,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _PopularService {
  const _PopularService({
    required this.id,
    required this.label,
    required this.asset,
  });

  final String id;
  final String label;
  final String asset;
}
