import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/admin_tracking_provider.dart';
import '../../providers/app_providers.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/more_menu_tile.dart';

class AdminLiveScreen extends StatefulWidget {
  const AdminLiveScreen({super.key});

  @override
  State<AdminLiveScreen> createState() => _AdminLiveScreenState();
}

class _AdminLiveScreenState extends State<AdminLiveScreen> {
  final MapController _mapController = MapController();
  AdminTrackingProvider? _admin;
  bool _pollingStarted = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_pollingStarted) {
      _pollingStarted = true;
      _admin = context.read<AdminTrackingProvider>();
      _admin!.startPolling();
    }
  }

  @override
  void dispose() {
    _admin?.stopPolling();
    _mapController.dispose();
    super.dispose();
  }

  List<Marker> _buildMarkers(List<Map<String, dynamic>> staff) {
    final markers = <Marker>[];
    for (final s in staff) {
      final lat = s['latitude'];
      final lng = s['longitude'];
      if (lat == null || lng == null) continue;
      final color = StaffStatusUtils.color(s['status']?.toString());
      markers.add(
        Marker(
          point: LatLng(double.parse(lat.toString()), double.parse(lng.toString())),
          width: 36,
          height: 36,
          child: Icon(Icons.person_pin_circle, color: color, size: 36),
        ),
      );
    }
    return markers;
  }

  LatLng _mapCenter(List<Map<String, dynamic>> staff) {
    for (final s in staff) {
      final lat = s['latitude'];
      final lng = s['longitude'];
      if (lat != null && lng != null) {
        return LatLng(double.parse(lat.toString()), double.parse(lng.toString()));
      }
    }
    return const LatLng(18.752, 73.405);
  }

  String _relativeTime(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      return '${diff.inDays}d ago';
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final admin = context.watch<AdminTrackingProvider>();
    final auth = context.read<AuthProvider>();
    final markers = _buildMarkers(admin.staff);
    final center = _mapCenter(admin.staff);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Live Tracking'),
        actions: [
          IconButton(
            onPressed: admin.loading ? null : admin.refresh,
            icon: admin.loading
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary))
                : const Icon(Icons.refresh),
          ),
          IconButton(
            onPressed: () async {
              admin.stopPolling();
              await auth.logout();
              if (context.mounted) context.go('/login');
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            width: double.infinity,
            color: AppColors.primary.withValues(alpha: 0.1),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    '${admin.onDutyCount} on duty  •  ${admin.staff.length} total',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
                if (admin.lastUpdated != null)
                  Text(
                    'Updated ${TimeOfDay.fromDateTime(admin.lastUpdated!).format(context)}',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
              ],
            ),
          ),
          SizedBox(
            height: 260,
            child: Stack(
              children: [
                FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(initialCenter: center, initialZoom: 11),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.multipestcare.pest99_tracking_app',
                    ),
                    MarkerLayer(markers: markers),
                  ],
                ),
                Positioned(
                  bottom: 8,
                  left: 8,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.surface.withValues(alpha: 0.95),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _legendDot(AppColors.successText, 'On duty'),
                        const SizedBox(width: 10),
                        _legendDot(AppColors.warning, 'Idle'),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (admin.error != null)
            Padding(
              padding: const EdgeInsets.all(8),
              child: Text(admin.error!, style: const TextStyle(color: AppColors.danger, fontSize: 12)),
            ),
          Expanded(
            child: admin.staff.isEmpty && !admin.loading
                ? const EmptyState(
                    message: 'No staff with active GPS yet.\nTechnicians appear here when checked in.',
                    icon: Icons.groups_outlined,
                  )
                : ListView.separated(
                    padding: const EdgeInsets.all(AppSpacing.screenEdge),
                    itemCount: admin.staff.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) {
                      final s = admin.staff[i];
                      final status = s['status']?.toString();
                      final color = StaffStatusUtils.color(status);
                      return Card(
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                          leading: CircleAvatar(
                            backgroundColor: color.withValues(alpha: 0.15),
                            child: Icon(Icons.person, color: color),
                          ),
                          title: Text(
                            s['name']?.toString() ?? 'Staff',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          subtitle: Text(
                            '${StaffStatusUtils.label(status)}'
                            '${s['city'] != null ? ' • ${s['city']}' : ''}'
                            '${s['distance_today_km'] != null ? ' • ${s['distance_today_km']} km' : ''}',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
                          ),
                          trailing: s['last_ping_at'] != null
                              ? Text(_relativeTime(s['last_ping_at'].toString()), style: Theme.of(context).textTheme.labelSmall)
                              : null,
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _legendDot(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.person_pin_circle, color: color, size: 16),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
